import express from 'express';
import sqlite3 from 'sqlite3';
import bodyParser from 'body-parser';
import cors from 'cors';
import rateLimit from 'express-rate-limit'; // Importing express-rate-limit


const app = express();
const port = 3000;
const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;

const options = {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
    timeZone: timeZone
};

const formatDateTime = (dateTime, options) => {
    const formatted = new Date(dateTime).toLocaleString('en-US', options);
    const [datePart, timePart] = formatted.split(', ');
    const [month, day, year] = datePart.split('/');
    const [hour, minute, second] = timePart.split(':');
    return `${year}-${month}-${day}T${hour}:${minute}:${second}`;
};

const UTCtoISOFormat = (dateTimeRange, options) => {
    const { start: startUTC, end: endUTC } = dateTimeRange;
    const startLocalISO = formatDateTime(startUTC, options);
    const endLocalISO = formatDateTime(endUTC, options);
    return { startLocalISO, endLocalISO };
};

// Express rate limit configuration
const limiter = rateLimit({
    windowMs: 5 * 60 * 1000, // 5 minutes
    max: 100, // Limit each IP to 100 requests per windowMs
    message: 'Too many requests from this IP, please try again after 5 minutes',
});

app.use(cors());
app.use(bodyParser.json());

const db = new sqlite3.Database('./reports.db', (err) => {
    if (err) {
        console.error('Could not connect to database', err);
    } else {
        console.log('Connected to SQLite database');
    }
});

db.serialize(() => {
    db.run(`PRAGMA foreign_keys=OFF;`, () => {
        console.log('Foreign keys off for SQLite3');
    });

    db.get(`SELECT name FROM sqlite_master WHERE type='table' AND name='reports_detail'`, (err, table) => {
        if (err) {
            console.error("Error verifying the table structure:", err.message);
        } else if (!table) {
            console.error("Table 'reports_detail' does not exist in the database.");
        } else {
            console.log("Table 'reports_detail' exists in the database.");
        }
    });
});

app.post('/query', limiter, async (req, res) => {
    console.log(req.body);
    const { idArray, dateTimeRange, mode } = req.body;

    if (idArray.length === 0 || !mode) {
        res.status(400).json({ error: 'Invalid request body' });
        return;
    }

    try {
        // 步骤1：根据privkey查询对应的hashed_adv_key
        const keyMapQuery = `
            SELECT private_key, hashed_adv_key
            FROM keyMap 
            WHERE private_key IN (${idArray.map(() => '?').join(',')})
        `;

        const keyMapRows = await new Promise((resolve, reject) => {
            db.all(keyMapQuery, idArray, (err, rows) => {
                if (err) reject(err);
                else resolve(rows);
            });
        });

        // 2. 构建双向映射关系
        const privToHashed = new Map();  // privkey → hashed_adv_key
        const hashedToPriv = new Map();  // hashed_adv_key → privkey

        keyMapRows.forEach(row => {
            privToHashed.set(row.private_key, row.hashed_adv_key);
            hashedToPriv.set(row.hashed_adv_key, row.private_key);
        });

        // 3. 获取实际用于查询的hashed_adv_keys
        const hashedAdvKeys = Array.from(privToHashed.values());
        if (hashedAdvKeys.length === 0) {
            return res.status(404).json({ error: 'No matching keys found' });
        }

        // 步骤2：根据hashed_adv_key查询reports_detail表
        if (mode === "realtime") {
            const query = `
                SELECT t.*
                FROM reports_detail t
                JOIN (
                    SELECT id, MAX(isodatetime) AS latest_isodatetime
                    FROM reports_detail
                    WHERE id IN (${hashedAdvKeys.map(() => '?').join(',')})
                    GROUP BY id
                ) sub
                ON t.id = sub.id AND t.isodatetime = sub.latest_isodatetime
                WHERE t.id IN (${hashedAdvKeys.map(() => '?').join(',')})
            `;

            const params = [...hashedAdvKeys, ...hashedAdvKeys];
            const rows = await new Promise((resolve, reject) => {
                db.all(query, params, (err, rows) => {
                    if (err) reject(err);
                    else resolve(rows);
                });
            });
            // 5. 将结果中的id替换回原始privkey
            const result = rows.map(row => ({
                ...row,
                id: hashedToPriv.get(row.id) || row.id // 保留原值如果找不到映射
            }));
            res.status(200).json({ data: result });
        }
        else if (mode === "timerange") {
            if (!dateTimeRange?.start || !dateTimeRange?.end) {
                return res.status(400).json({ error: 'Invalid dateTimeRange' });
            }

            const { startLocalISO, endLocalISO } = UTCtoISOFormat(dateTimeRange, options);
            const query = `
                SELECT * 
                FROM reports_detail 
                WHERE id IN (${hashedAdvKeys.map(() => '?').join(',')}) 
                AND isodatetime BETWEEN ? AND ?
            `;

            const params = [...hashedAdvKeys, startLocalISO, endLocalISO];
            const rows = await new Promise((resolve, reject) => {
                db.all(query, params, (err, rows) => {
                    if (err) reject(err);
                    else resolve(rows);
                });
            });
            // 5. 将结果中的id替换回原始privkey
            const result = rows.map(row => ({
                ...row,
                id: hashedToPriv.get(row.id) || row.id // 保留原值如果找不到映射
            }));
            res.status(200).json({ data: result });
        }

    } catch (err) {
        res.status(500).json({ error: err.message });
    }
});

app.listen(port, () => {
    console.log(`Server running on port ${port}`);
});
