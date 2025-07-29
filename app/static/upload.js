const Upload = {
    compressImage: async function (file, maxWidth = 1000, maxHeight = 1000, quality = 0.7) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (event) => {
                const img = new Image();
                img.src = event.target.result;

                img.onload = () => {
                    const canvas = document.createElement("canvas");
                    let width = img.width;
                    let height = img.height;

                    if (width > maxWidth || height > maxHeight) {
                        if (width > height) {
                            height *= maxWidth / width;
                            width = maxWidth;
                        } else {
                            width *= maxHeight / height;
                            height = maxHeight;
                        }
                    }

                    canvas.width = width;
                    canvas.height = height;

                    const ctx = canvas.getContext("2d");
                    ctx.drawImage(img, 0, 0, width, height);

                    canvas.toBlob((blob) => {
                        resolve(blob);
                    }, "image/jpeg", quality);
                };

                img.onerror = (error) => reject(error);
            };

            reader.readAsDataURL(file);
        });
    },

    handleFormSubmit: async function (event) {
        //calculate time to process all files
        const startTime = performance.now();
        event.preventDefault();

        const form = document.getElementById("upload-form");
        const fileInput = document.getElementById("file-input");
        const statusDiv = document.getElementById("status");

        // default div state
        statusDiv.style.display = "none";
        statusDiv.textContent = "";

        const files = fileInput.files;
        if (files.length === 0) {
            statusDiv.textContent = "Please select images.";
            statusDiv.style.display = "block";
            return;
        }

        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            let file = files[i];

            if (file.type === "image/heic" || file.type === "image/heif") {
                statusDiv.textContent = `Converting ${file.name} from HEIC to PNG...`;
                statusDiv.style.display = "block";

                try {
                    const pngBlob = await heic2any({
                        blob: file,
                        toType: "image/png",
                        quality: 0.9,
                    });
                    file = new File([pngBlob], file.name.replace(/\.heic$/i, ".png"), { type: "image/png" });
                } catch (error) {
                    console.error(`Error converting ${file.name}:`, error);
                    statusDiv.textContent = `❌ Failed to convert ${file.name}`;
                    statusDiv.style.display = "block";
                    return;
                }
            }

            statusDiv.textContent = `Compressing ${file.name}...`;
            statusDiv.style.display = "block";

            try {
                const compressedBlob = await Upload.compressImage(file, 1000, 1000, 0.7);
                formData.append("files", compressedBlob, file.name);
            } catch (error) {
                console.error(`Error compressing ${file.name}:`, error);
                statusDiv.textContent = `❌ Failed to compress ${file.name}`;
                statusDiv.style.display = "block";
                return;
            }
        }
        
        statusDiv.textContent = "Uploading images...";
        statusDiv.style.display = "block";
        try {
            const response = await fetch("/upload", {
                method: "POST",
                body: formData,
            });

            if (response.ok) {
                statusDiv.textContent = "✅ Images uploaded successfully!";
                statusDiv.style.display = "block";
                setTimeout(() => {
                    location.reload();
                }, 500);
            } else {
                let errorMsg = "❌ Upload failed.";
                try {
                    const errorJson = await response.json();
                    if (errorJson && errorJson.message) {
                        errorMsg += ` ${errorJson.message}`;
                    }
                } catch {
                    // ignore JSON parse errors, keep errorMsg as is
                }
                statusDiv.textContent = errorMsg;
                statusDiv.style.display = "block";
            }
        } catch (error) {
            console.error("Error uploading images:", error);
            statusDiv.textContent = "❌ Upload failed.";
            statusDiv.style.display = "block";
        }
        const endTime = performance.now();
        console.log(`Total processing time: ${(endTime - startTime).toFixed(2)} ms`);
        statusDiv.textContent += ` Processing time: ${(endTime - startTime).toFixed(2)} ms`;
        statusDiv.style.display = "block";
    },

    handleManualFormSubmit: async function (event) {
        event.preventDefault();

        const form = document.getElementById("manual-form");
        const usdotInput = document.getElementById("usdot-input");
        const statusDiv = document.getElementById("status");
        
        // Default div state
        statusDiv.style.display = "none";
        statusDiv.textContent = "";

        const usdotNumbers = usdotInput.value.trim();
        if (!usdotNumbers) {
            statusDiv.textContent = "Please enter USDOT numbers.";
            statusDiv.style.display = "block";
            return;
        }

        const formData = new FormData();
        formData.append("manual_usdots", usdotNumbers);

        statusDiv.textContent = "Processing USDOT numbers...";
        statusDiv.style.display = "block";

        try {
            const response = await fetch("/upload", {
                method: "POST",
                body: formData,
            });

            if (response.ok) {
                const result = await response.json();
                statusDiv.textContent = `✅ Processed ${result.valid_usdots.length} USDOT numbers successfully! ${result.successful_lookups} carrier records found.`;
                if (result.invalid_usdots.length > 0) {
                    statusDiv.textContent += ` (${result.invalid_usdots.length} invalid numbers ignored)`;
                }
                statusDiv.style.display = "block";
                setTimeout(() => {
                    location.reload();
                }, 500);
            } else {
                const errorData = await response.json();
                statusDiv.textContent = `❌ Error: ${errorData.detail || 'Processing failed'}`;
                statusDiv.style.display = "block";
            }
        } catch (error) {
            console.error("Error processing manual USDOT input:", error);
            statusDiv.textContent = "❌ Processing failed.";
            statusDiv.style.display = "block";
        }
    },

    init: function () {
        const uploadForm = document.getElementById("upload-form");
        if (uploadForm) {
            uploadForm.addEventListener("submit", Upload.handleFormSubmit);
        }

        const manualForm = document.getElementById("manual-form");
        if (manualForm) {
            manualForm.addEventListener("submit", Upload.handleManualFormSubmit);
        }
    },
};

document.addEventListener("DOMContentLoaded", Upload.init);