
/**
 * Compress image before uploading
 * @param {File} file - Image file
 * @param {number} maxWidth - Max width of resized image
 * @param {number} maxHeight - Max height of resized image
 * @param {number} quality - Compression quality (0 to 1)
 * @returns {Promise<Blob>} - Compressed image blob
 */
async function compressImage(file, maxWidth = 1000, maxHeight = 1000, quality = 0.7) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        
        reader.onload = (event) => {
            const img = new Image();
            img.src = event.target.result;

            img.onload = () => {
                const canvas = document.createElement("canvas");
                let width = img.width;
                let height = img.height;

                // Resize while keeping aspect ratio
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

                // Compress and return blob
                canvas.toBlob((blob) => {
                    resolve(blob);
                }, "image/jpeg", quality);
            };

            img.onerror = (error) => reject(error);
        };

        reader.readAsDataURL(file);
    });
}

/**
 * Handle form submission with multiple images
 * - Compresses images before upload
 * - Shows upload status
 */
document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("upload-form");
    const fileInput = document.getElementById("file-input");
    const statusDiv = document.getElementById("status");
    const progressDiv = document.getElementById("progress");

    // Event Listener for file input change
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        
        const files = fileInput.files;
        if (files.length === 0) {
            statusDiv.textContent = "Please select images.";
            return;
        }

        const formData = new FormData();
        
        // Compress and add each image to FormData
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            console.log(file.name);

            statusDiv.textContent = `Compressing ${file.name}...`;
            
            try {
                const compressedBlob = await compressImage(file, 1000, 1000, 0.7);
                formData.append("files", compressedBlob, file.name);
            } catch (error) {
                console.error(`Error compressing ${file.name}:`, error);
                statusDiv.textContent = `❌ Failed to compress ${file.name}`;
                return;
            }
        }

        // Show upload status
        statusDiv.textContent = "Uploading images...";
        
        try {
            const response = await fetch("/upload", {
                method: "POST",
                body: formData,
            });

            if (response.ok) {
                statusDiv.textContent = "✅ Images uploaded successfully!";
                setTimeout(() => {
                    location.reload(); // Refresh the page after successful upload
                }, 500); // Optional delay for user to see the success message
            } else {
                statusDiv.textContent = "❌ Upload failed.";
            }
        } catch (error) {
            console.error("Error uploading images:", error);
            statusDiv.textContent = "❌ Upload failed.";
        }
    });

});