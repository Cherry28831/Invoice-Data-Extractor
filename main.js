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

    mainWindow.loadFile('frontend/index.html');

    ipcMain.handle('select-output-folder', async () => {
        const result = await dialog.showOpenDialog(mainWindow, {
            properties: ['openDirectory']
        });

        return result.filePaths[0] || null;
    });

    ipcMain.on('process-pdfs', (event, { filePaths, apiKey, outputFolder, filename }) => {
        console.log(`Processing PDFs: ${filePaths} with API Key: ${apiKey}`);
        console.log(`Saving output to: ${path.join(outputFolder, filename)}`);

        // Correct path to backend.py
        const backendPath = path.join(__dirname, 'backend', 'backend.py');
        console.log(`Backend script path: ${backendPath}`); // Debug log

        // Pass all file paths to the backend script
        const pythonProcess = spawn('python', [backendPath, ...filePaths, apiKey, outputFolder, filename]);

        let outputData = '';
        let errorData = '';

        // Capture stdout from Python script
        pythonProcess.stdout.on('data', (data) => {
            outputData += data.toString();
        });

        // Capture stderr (error output)
        pythonProcess.stderr.on('data', (data) => {
            errorData += data.toString();
        });

        // Handle process completion
        pythonProcess.on('close', (code) => {
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