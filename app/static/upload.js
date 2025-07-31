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

    clearStatus: function (statusDiv) {
        statusDiv.style.display = "none";
        statusDiv.innerHTML = "";
    },

    appendAlert: function (statusDiv, type, message) {
        const alert = document.createElement("div");
        alert.className = `alert alert-${type} alert-dismissible fade show mt-2`;
        alert.role = "alert";
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close" style="position:absolute;top:8px;right:12px;"></button>
        `;
        statusDiv.appendChild(alert);
        statusDiv.style.display = "block";

        // Optional: Dismiss all alerts when the close button is clicked
        const closeBtn = alert.querySelector(".btn-close");
        if (closeBtn) {
            closeBtn.addEventListener("click", () => {
                // Remove all alerts inside statusDiv
                statusDiv.innerHTML = "";
                statusDiv.style.display = "none";
            });
        }
    },

    clearStatus: function (statusDiv) {
    statusDiv.style.display = "none";
    statusDiv.innerHTML = '<div id="status-message"></div>'; // Always keep a single message div
    },

    setStatusMessage: function (statusDiv, type, message) {
        let msgDiv = statusDiv.querySelector("#status-message");
        if (!msgDiv) {
            msgDiv = document.createElement("div");
            msgDiv.id = "status-message";
            statusDiv.appendChild(msgDiv);
        }
        msgDiv.className = `alert alert-${type} mt-2`;
        msgDiv.innerHTML = message;
        statusDiv.style.display = "block";
    },

    buildFormData: async function (statusDiv) {
        const formData = new FormData();
        // Get files from upload-form
        const fileInput = document.getElementById("file-input");
        if (fileInput && fileInput.files.length > 0) {
            for (let i = 0; i < fileInput.files.length; i++) {
                let file = fileInput.files[i];
                // Convert HEIC/HEIF if needed
                Upload.setStatusMessage(statusDiv, "info", `Compressing ${file.name}...`);
                if (file.type === "image/heic" || file.type === "image/heif") {
                    try {
                        const pngBlob = await heic2any({
                            blob: file,
                            toType: "image/png",
                            quality: 0.9,
                        });
                        file = new File([pngBlob], file.name.replace(/\.heic$/i, ".png"), { type: "image/png" });
                    } catch (error) {
                        throw new Error(`❌ Failed to convert ${file.name}`);
                    }
                }
                try {
                    const compressedBlob = await Upload.compressImage(file, 1000, 1000, 0.7);
                    formData.append("files", compressedBlob, file.name);
                } catch (error) {
                    throw new Error(`❌ Failed to compress ${file.name}`);
                }
            }
        }
        // Get manual USDOTs from manual-form
        const usdotInput = document.getElementById("usdot-input");
        if (usdotInput && usdotInput.value.trim()) {
            formData.append("manual_usdots", usdotInput.value.trim());
        }
        // Add ignore_duplicated_usdots if present
        const ignoreCheckbox = document.getElementById("ignore_duplicated_usdots");
        if (ignoreCheckbox) {
            formData.append("ignore_duplicated_usdots", ignoreCheckbox.checked ? "true" : "false");
        }
        return formData;
    },

    handleUnifiedFormSubmit: async function (event) {
        event.preventDefault();
        const startTime = performance.now();
        const statusDiv = document.getElementById("status");
        Upload.clearStatus(statusDiv);

        let hasFiles = false;
        let hasManual = false;
        const fileInput = document.getElementById("file-input");
        if (fileInput && fileInput.files.length > 0) hasFiles = true;
        const usdotInput = document.getElementById("usdot-input");
        if (usdotInput && usdotInput.value.trim()) hasManual = true;

        if (!hasFiles && !hasManual) {
            Upload.appendAlert(statusDiv, "warning", "Please select images or enter USDOT numbers.");
            return;
        }

        if (hasFiles) {
            Upload.appendAlert(statusDiv, "info", "Preparing images for upload...");
        }
        if (hasManual) {
            Upload.appendAlert(statusDiv, "info", "Preparing USDOT numbers for processing...");
        }

        let formData;
        try {
            formData = await Upload.buildFormData(statusDiv);
            statusDiv.querySelector("#status-message").remove(); // Or set to empty string

        } catch (error) {
            Upload.appendAlert(statusDiv, "danger", error.message);
            return;
        }

        Upload.appendAlert(statusDiv, "info", "Uploading data...");
        try {
            const response = await fetch("/upload", {
                method: "POST",
                body: formData,
            });

            statusDiv.innerHTML = ""; // Clear previous messages

            if (response.ok) {
                const result = await response.json();
                Upload.appendAlert(statusDiv, "success", `✅ Data processed successfully! Processing time: ${(performance.now() - startTime).toFixed(2)} ms`);

                // Show warnings for USDOTs not found and invalid files
                if (result.records) {
                    const notFound = result.records
                        .filter(r => !r.safer_lookup_success && r.dot_reading !== "00000000")
                        .map(r => r.dot_reading);
                    if (notFound.length > 0) {
                        Upload.appendAlert(
                            statusDiv,
                            "warning",
                            `<strong>Warning:</strong> The following USDOT numbers were not found in SAFER: <br>${notFound.join(", ")}`
                        );
                    }
                }
                if (result.invalid_files && result.invalid_files.length > 0) {
                    Upload.appendAlert(
                        statusDiv,
                        "danger",
                        `<strong>Invalid files:</strong> Could not extract USDOT or image format not valid <br>${result.invalid_files.join(", ")}`
                    );
                }

                // Dynamically refresh the table if Filters is available
                if (window.Filters && typeof Filters.fetchData === "function") {
                    Filters.offset = 0;
                    Filters.hasMoreData = true;
                    await Filters.fetchData(false);
                }
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
                Upload.appendAlert(statusDiv, "danger", errorMsg);
            }
        } catch (error) {
            console.error("Error uploading data:", error);
            Upload.appendAlert(statusDiv, "danger", "❌ Upload failed.");
        }
    },

    init: function () {
        const uploadForm = document.getElementById("upload-form");
        if (uploadForm) {
            uploadForm.addEventListener("submit", Upload.handleUnifiedFormSubmit);
        }
        const manualForm = document.getElementById("manual-form");
        if (manualForm) {
            manualForm.addEventListener("submit", Upload.handleUnifiedFormSubmit);
        }
    },
};

document.addEventListener("DOMContentLoaded", Upload.init);