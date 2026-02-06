<script setup>
import { ref, computed } from 'vue'
import { uploadApi } from '@/services/api'

const props = defineProps({
  modelValue: String,
  label: {
    type: String,
    default: 'Upload Image'
  },
  placeholder: String
})

const emit = defineEmits(['update:modelValue'])

const fileInput = ref(null)
const isUploading = ref(false)
const uploadProgress = ref(0)
const uploadError = ref(null)
const previewUrl = computed(() => props.modelValue)

function triggerFileSelect() {
  fileInput.value.click()
}

async function handleFileChange(event) {
  const file = event.target.files[0]
  if (!file) return

  // Validate file type
  const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/webp']
  if (!allowedTypes.includes(file.type)) {
    uploadError.value = 'Invalid file type. Please upload PNG, JPG, GIF, or WebP.'
    return
  }

  // Validate file size (10MB max)
  const maxSize = 10 * 1024 * 1024
  if (file.size > maxSize) {
    uploadError.value = 'File too large. Maximum size is 10MB.'
    return
  }

  isUploading.value = true
  uploadError.value = null
  uploadProgress.value = 0

  try {
    // Show local preview immediately
    const localPreview = URL.createObjectURL(file)

    const response = await uploadApi.uploadBanner(file)

    if (response.data.success) {
      emit('update:modelValue', response.data.url)
      URL.revokeObjectURL(localPreview)
    } else {
      uploadError.value = response.data.error || 'Upload failed'
    }
  } catch (error) {
    console.error('Upload error:', error)
    uploadError.value = 'Upload failed. Please try again.'
  } finally {
    isUploading.value = false
    uploadProgress.value = 0
    // Reset file input
    if (fileInput.value) {
      fileInput.value.value = ''
    }
  }
}

function removeImage() {
  emit('update:modelValue', '')
}
</script>

<template>
  <div class="upload-container">
    <label v-if="label" class="upload-label">{{ label }}</label>

    <!-- Image Preview -->
    <div v-if="previewUrl" class="image-preview-wrapper">
      <div class="image-preview">
        <img :src="previewUrl" alt="Banner preview" class="preview-img" />
        <button @click="removeImage" class="remove-btn" type="button">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
    </div>

    <!-- Upload Area -->
    <div v-else class="upload-area" :class="{ uploading: isUploading, error: uploadError }" @click="!isUploading && triggerFileSelect()">
      <input
        ref="fileInput"
        type="file"
        accept="image/png,image/jpeg,image/jpg,image/gif,image/webp"
        @change="handleFileChange"
        class="file-input"
      />

      <div v-if="isUploading" class="upload-state">
        <div class="spinner"></div>
        <p>Uploading... {{ uploadProgress }}%</p>
      </div>

      <div v-else-if="uploadError" class="upload-state error">
        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="8" x2="12" y2="12"></line>
          <line x1="12" y1="16" x2="12.01" y2="16"></line>
        </svg>
        <p>{{ uploadError }}</p>
        <button @click.stop="triggerFileSelect" class="retry-btn">Try Again</button>
      </div>

      <div v-else class="upload-state">
        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="17 8 12 4 12 4"></polyline>
          <line x1="12" y1="3" x2="12" y2="15"></line>
        </svg>
        <p>{{ placeholder || 'Click to upload or enter image URL' }}</p>
        <span class="upload-hint">PNG, JPG, GIF, WebP (max 10MB)</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.upload-container {
  width: 100%;
}

.upload-label {
  display: block;
  font-size: 0.875rem;
  font-weight:  500;
  color: #b5bac1;
  margin-bottom: 0.375rem;
}

.file-input {
  display: none;
}

.image-preview-wrapper {
  margin-bottom: 1rem;
}

.image-preview {
  position: relative;
  display: inline-block;
  width: 100%;
  max-width: 400px;
  border-radius: 0.5rem;
  overflow: hidden;
}

.preview-img {
  width: 100%;
  height: auto;
  display: block;
  border-radius: 0.5rem;
}

.remove-btn {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  width: 2rem;
  height: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.7);
  border: none;
  border-radius: 0.375rem;
  color: white;
  cursor: pointer;
  transition: background 0.15s ease;
}

.remove-btn:hover {
  background: rgba(231, 76, 60, 0.9);
}

.upload-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  background: #383a40;
  border: 2px dashed #4e5058;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.15s ease;
}

.upload-area:hover:not(.uploading) {
  background: #404249;
  border-color: #5865f2;
}

.upload-area.uploading {
  opacity: 0.7;
  cursor: not-allowed;
}

.upload-area.error {
  border-color: #da373c;
  background: rgba(220, 35, 45, 0.1);
}

.upload-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  color: #dbdee1;
}

.upload-state p {
  margin: 0;
  font-size: 0.875rem;
}

.upload-hint {
  font-size: 0.75rem;
  color: #80848e;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 3px solid #5865f2;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.retry-btn {
  padding: 0.375rem 0.75rem;
  background: #5865f2;
  border: none;
  border-radius: 0.25rem;
  color: white;
  font-size: 0.75rem;
  cursor: pointer;
  transition: background 0.15s ease;
}

.retry-btn:hover {
  background: #4752c4;
}
</style>
