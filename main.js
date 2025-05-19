const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const { spawn } = require('child_process');
const path = require('path');

console.log(`Current working directory: ${process.cwd()}`); // Debug log

let mainWindow;

app.whenReady().then(() => {
    mainWindow = new BrowserWindow({
        width: 900,
        height: 700,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false
        }
    });

    mainWindow.loadFile(path.join(__dirname, 'frontend', 'index.html'));

    ipcMain.handle('select-output-folder', async () => {
        const result = await dialog.showOpenDialog(mainWindow, {
            properties: ['openDirectory']
        });

        return result.filePaths[0] || null;
    });

    ipcMain.on('process-pdfs', (event, { filePaths, apiKey, outputFolder, filename }) => {
        console.log(`Processing PDFs: ${filePaths} with API Key: ${apiKey}`);
        console.log(`Saving output to: ${path.join(outputFolder, filename)}`);

        // Path to the standalone .exe you built
        const backendPath = path.join(__dirname, 'backend', 'invoice-backend.exe');
        console.log(`Backend script path: ${backendPath}`); // Debug log

        // Arguments that your Python script expects
        const args = [...filePaths, apiKey, outputFolder, filename];

        // Spawn the executable directly (no 'python' command)
        const backendProcess = spawn(backendPath, args);

        let outputData = '';
        let errorData = '';

        backendProcess.stdout.on('data', (data) => {
            outputData += data.toString();
        });

        backendProcess.stderr.on('data', (data) => {
            errorData += data.toString();
        });

        backendProcess.on('close', (code) => {
            if (code === 0) {
                console.log(`Processing Complete: ${outputData}`);
                event.reply('processing-result', { success: true, output: outputData.trim() });
            } else {
                console.error(`Processing Error: ${errorData}`);
                event.reply('processing-result', { success: false, error: errorData.trim() });
            }
        });
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit();
});