<script setup lang="ts">
type UploadState = 'pending' | 'compressing' | 'uploading' | 'uploaded' | 'error'

interface UploadFieldItem {
  id: string
  name: string
  status: UploadState
  message: string
  previewUrl?: string | null
  thumbnailUrl?: string | null
}

const props = defineProps<{
  label: string
  section: string
  min: number
  max: number
  items: UploadFieldItem[]
  disabled?: boolean
  error?: string
}>()

const emit = defineEmits<{
  select: [files: File[]]
  remove: [itemId: string]
}>()

function onInputChange(event: Event): void {
  const target = event.target as HTMLInputElement
  const files = Array.from(target.files ?? [])
  emit('select', files)
  target.value = ''
}

function onItemRemoved(itemId: string): void {
  emit('remove', itemId)
}
</script>

<template>
  <article class="upload-card">
    <div class="upload-card__meta">
      <p class="upload-card__section">{{ props.section }}</p>
      <h3 class="upload-card__title">{{ props.label }}</h3>
      <p class="upload-card__limits">Required {{ props.min }} to {{ props.max }} photo(s)</p>
    </div>

    <div class="upload-actions">
      <label class="upload-dropzone">
        <input
          class="upload-dropzone__input"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          :multiple="props.max > 1"
          :disabled="props.disabled"
          @change="onInputChange"
        />
        <span class="upload-dropzone__text">Choose from library</span>
      </label>

      <label class="upload-dropzone upload-dropzone--camera">
        <input
          class="upload-dropzone__camera-input"
          type="file"
          accept="image/*"
          capture="environment"
          :disabled="props.disabled"
          @change="onInputChange"
        />
        <span class="upload-dropzone__text">Take photo</span>
      </label>
    </div>

    <p v-if="props.error" class="upload-card__error">{{ props.error }}</p>

    <ul class="upload-list" aria-live="polite">
      <li v-for="item in props.items" :key="item.id" class="upload-list__item">
        <img
          v-if="item.previewUrl || item.thumbnailUrl"
          class="upload-list__thumbnail"
          :src="item.previewUrl || item.thumbnailUrl || undefined"
          :alt="item.name"
        />

        <div class="upload-list__details">
          <span class="upload-list__name">{{ item.name }}</span>
          <span class="upload-list__status" :data-state="item.status">{{ item.message }}</span>
        </div>

        <button
          class="upload-list__remove"
          type="button"
          :disabled="props.disabled"
          @click="onItemRemoved(item.id)"
        >
          Remove
        </button>
      </li>
    </ul>
  </article>
</template>
