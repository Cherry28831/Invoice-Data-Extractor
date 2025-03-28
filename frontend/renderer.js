const { ipcRenderer } = require('electron');
const path = require('path');

document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('fileInput');
    const apiKeyInput = document.getElementById('apiKey');
    const outputFolderButton = document.getElementById('outputFolderButton');
    const outputFolderPath = document.getElementById('outputFolderPath');
    const filenameInput = document.getElementById('filename');
    const processButton = document.getElementById('processButton');
    const outputDiv = document.getElementById('output');

    // Select output folder
    outputFolderButton.addEventListener('click', async () => {
        const folder = await ipcRenderer.invoke('select-output-folder');
        if (folder) {
            outputFolderPath.value = folder;
        }
    });

    processButton.addEventListener('click', () => {
        if (fileInput.files.length === 0) {
            alert('Please select at least one PDF file.');
            return;
        }

        if (!apiKeyInput.value.trim()) {
            alert('Please enter your LLM API key.');
            return;
        }

        if (!outputFolderPath.value.trim()) {
            alert('Please select an output folder.');
            return;
        }

        let filename = filenameInput.value.trim();
        if (!filename) {
            filename = "invoice_data.xlsx";  // Default filename if user leaves it empty
        } else if (!filename.endsWith(".xlsx")) {
            filename += ".xlsx";  // Ensure correct file extension
        }

        // Get all selected file paths
        const filePaths = Array.from(fileInput.files).map(file => file.path);
        const apiKey = apiKeyInput.value.trim();
        const outputFolder = outputFolderPath.value.trim();

        // Disable the process button and show a loading indicator
        processButton.disabled = true;
        processButton.innerText = "Processing...";

        // Send data to `main.js`
        console.log("Sending data:", { filePaths, apiKey, outputFolder, filename });
        ipcRenderer.send('process-pdfs', { filePaths, apiKey, outputFolder, filename });

        // Handle response from `backend.py`
        ipcRenderer.on('processing-result', (event, result) => {
            // Re-enable the process button and reset its text
            processButton.disabled = false;
            processButton.innerText = "Process PDF";

            if (result.success) {
                outputDiv.innerText = `Processing Complete! \nSaved at: ${result.output}`;
            } else {
                outputDiv.innerText = `Error: ${result.error}`;
            }
        });
    });
});