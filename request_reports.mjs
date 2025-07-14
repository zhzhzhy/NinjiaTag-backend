import cron from 'node-cron';
import { exec } from 'child_process';

console.log('Waiting...');

cron.schedule('*/5 * * * *', () => {
    console.log('Running Python script...');
    exec('python3 request_reports.py', (error, stdout, stderr) => {
        if (error) {
            console.error(`Error executing script: ${error.message}`);
            return;
        }

        if (stderr) {
            console.error(`stderr: ${stderr}`);
            return;
        }

        console.log(`stdout: ${stdout}`);
    });
});