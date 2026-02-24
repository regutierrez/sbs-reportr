<script setup lang="ts">
type UploadState = 'pending' | 'compressing' | 'uploading' | 'uploaded' | 'error'

interface UploadFieldItem {
  id: string
  name: string
  status: UploadState
  message: string
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
}>()

function onInputChange(event: Event): void {
  const target = event.target as HTMLInputElement
  const files = Array.from(target.files ?? [])
  emit('select', files)
  target.value = ''
}
</script>

<template>
  <article class="upload-card">
    <div class="upload-card__meta">
      <p class="upload-card__section">{{ props.section }}</p>
      <h3 class="upload-card__title">{{ props.label }}</h3>
      <p class="upload-card__limits">Required {{ props.min }} to {{ props.max }} photo(s)</p>
    </div>

    <label class="upload-dropzone">
      <input
        class="upload-dropzone__input"
        type="file"
        accept="image/jpeg,image/png,image/webp"
        :multiple="props.max > 1"
        :disabled="props.disabled"
        @change="onInputChange"
      />
      <span class="upload-dropzone__text">Choose image{{ props.max > 1 ? 's' : '' }}</span>
    </label>

    <p v-if="props.error" class="upload-card__error">{{ props.error }}</p>

    <ul class="upload-list" aria-live="polite">
      <li v-for="item in props.items" :key="item.id" class="upload-list__item">
        <span class="upload-list__name">{{ item.name }}</span>
        <span class="upload-list__status" :data-state="item.status">{{ item.message }}</span>
      </li>
    </ul>
  </article>
</template>
