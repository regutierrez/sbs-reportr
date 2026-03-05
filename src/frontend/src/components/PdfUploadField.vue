<script setup lang="ts">
type UploadState = 'pending' | 'uploading' | 'uploaded' | 'error'

interface PdfUploadFieldItem {
  id: string
  name: string
  status: UploadState
  message: string
}

const props = defineProps<{
  label: string
  section: string
  items: PdfUploadFieldItem[]
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
  <article class="upload-card upload-card--pdf">
    <div class="upload-card__meta">
      <p class="upload-card__section">{{ props.section }}</p>
      <h3 class="upload-card__title">{{ props.label }}</h3>
      <p class="upload-card__limits">Optional · 1 PDF file</p>
    </div>

    <label class="upload-dropzone upload-dropzone--pdf">
      <input
        class="upload-dropzone__pdf-input"
        type="file"
        accept="application/pdf"
        :disabled="props.disabled"
        @change="onInputChange"
      />
      <span class="upload-dropzone__text">Choose PDF</span>
    </label>

    <p v-if="props.error" class="upload-card__error">{{ props.error }}</p>

    <ul class="upload-list" aria-live="polite">
      <li v-for="item in props.items" :key="item.id" class="upload-list__item upload-list__item--document">
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
