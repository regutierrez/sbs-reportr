<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

import { ApiError, createReportSession, saveReportFormFields, uploadReportImage } from '@/api'
import ImageUploadField from '@/components/ImageUploadField.vue'
import SectionHeader from '@/components/SectionHeader.vue'
import {
  useReportIntakeDraft,
  type UploadItem,
} from '@/composables/use-report-intake-draft'
import { PHOTO_GROUPS, type PhotoGroupConfig } from '@/constants/photo-groups'
import type { PhotoGroupName, ReportFormFields } from '@/types/report'
import { compressImageForUpload } from '@/utils/image-compression'

const router = useRouter()
const { confirmationReady, form, generatedDownloadUrl, selectionWarnings, sessionId, uploads } =
  useReportIntakeDraft()

const isSubmitting = ref(false)
const submitError = ref('')
const submitSuccess = ref('')

const fieldErrors = computed<Record<string, string>>(() => {
  const errors: Record<string, string> = {}

  if (!/^\d{4}-\d{2}$/.test(form.building_details.testing_date)) {
    errors.testing_date = 'Testing date is required.'
  }
  if (!form.building_details.building_name.trim()) {
    errors.building_name = 'Building name is required.'
  }
  if (!form.building_details.building_location.trim()) {
    errors.building_location = 'Building location is required.'
  }
  if (form.building_details.number_of_storey < 1) {
    errors.number_of_storey = 'Number of storey must be at least 1.'
  }

  if (form.superstructure.rebar_scanning.number_of_rebar_scan_locations < 1) {
    errors.number_of_rebar_scan_locations = 'Rebar scan locations must be at least 1.'
  }
  if (form.superstructure.rebound_hammer_test.number_of_rebound_hammer_test_locations < 1) {
    errors.number_of_rebound_hammer_test_locations =
      'Rebound hammer test locations must be at least 1.'
  }
  if (form.superstructure.concrete_core_extraction.number_of_coring_locations < 1) {
    errors.number_of_coring_locations = 'Coring locations must be at least 1.'
  }
  if (form.superstructure.rebar_extraction.number_of_rebar_samples_extracted < 1) {
    errors.number_of_rebar_samples_extracted = 'Rebar samples must be at least 1.'
  }
  if (!form.superstructure.restoration_works.non_shrink_grout_product_used.trim()) {
    errors.non_shrink_grout_product_used = 'Non-shrink grout product is required.'
  }
  if (!form.superstructure.restoration_works.epoxy_ab_used.trim()) {
    errors.epoxy_ab_used = 'Epoxy A&B product is required.'
  }

  if (form.substructure.concrete_core_extraction.number_of_foundation_locations < 1) {
    errors.number_of_foundation_locations = 'Foundation locations must be at least 1.'
  }
  if (form.substructure.concrete_core_extraction.number_of_foundation_cores_extracted < 1) {
    errors.number_of_foundation_cores_extracted = 'Foundation cores extracted must be at least 1.'
  }

  if (!form.signature.prepared_by.trim()) {
    errors.prepared_by = 'Prepared by is required.'
  }
  if (!form.signature.prepared_by_role.trim()) {
    errors.prepared_by_role = 'Role is required.'
  }

  return errors
})

const missingPhotoGroupLabels = computed(() => {
  return PHOTO_GROUPS.filter((group) => uploads[group.name].length < group.min).map(
    (group) => group.label,
  )
})

const canSubmit = computed(() => {
  return (
    Object.keys(fieldErrors.value).length === 0 &&
    missingPhotoGroupLabels.value.length === 0 &&
    !isSubmitting.value
  )
})

const photoGroupsByName = PHOTO_GROUPS.reduce(
  (accumulator, group) => {
    accumulator[group.name] = group
    return accumulator
  },
  {} as Record<PhotoGroupName, PhotoGroupConfig>,
)

function createItemId(): string {
  if (globalThis.crypto && 'randomUUID' in globalThis.crypto) {
    return globalThis.crypto.randomUUID()
  }

  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function releasePreviewUrls(items: UploadItem[]): void {
  for (const item of items) {
    URL.revokeObjectURL(item.previewUrl)
  }
}

function onFilesSelected(group: PhotoGroupConfig, files: File[]): void {
  releasePreviewUrls(uploads[group.name])

  const truncatedFiles = files.slice(0, group.max)
  uploads[group.name] = truncatedFiles.map((file) => ({
    id: createItemId(),
    name: file.name,
    file,
    previewUrl: URL.createObjectURL(file),
    status: 'pending',
    message: 'Queued',
    uploadedImage: null,
  }))

  selectionWarnings[group.name] =
    files.length > group.max
      ? `Only the first ${group.max} file(s) were kept for this group.`
      : ''
}

function photoGroupError(group: PhotoGroupConfig): string {
  if (uploads[group.name].length < group.min) {
    return `Add at least ${group.min} photo(s).`
  }

  return selectionWarnings[group.name]
}

function normalizeErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (typeof error.detail === 'string') {
      return error.detail
    }

    if (error.detail && typeof error.detail === 'object' && 'message' in error.detail) {
      const detail = error.detail as { message?: unknown }
      if (typeof detail.message === 'string') {
        return detail.message
      }
    }

    return `Request failed (${error.status}).`
  }

  if (error instanceof Error) {
    return error.message
  }

  return 'Unexpected error while uploading report data.'
}

function buildFormPayload(): ReportFormFields {
  return {
    building_details: {
      testing_date: form.building_details.testing_date,
      building_name: form.building_details.building_name.trim(),
      building_location: form.building_details.building_location.trim(),
      number_of_storey: form.building_details.number_of_storey,
    },
    superstructure: {
      rebar_scanning: {
        number_of_rebar_scan_locations: form.superstructure.rebar_scanning.number_of_rebar_scan_locations,
      },
      rebound_hammer_test: {
        number_of_rebound_hammer_test_locations:
          form.superstructure.rebound_hammer_test.number_of_rebound_hammer_test_locations,
      },
      concrete_core_extraction: {
        number_of_coring_locations: form.superstructure.concrete_core_extraction.number_of_coring_locations,
      },
      rebar_extraction: {
        number_of_rebar_samples_extracted:
          form.superstructure.rebar_extraction.number_of_rebar_samples_extracted,
      },
      restoration_works: {
        non_shrink_grout_product_used:
          form.superstructure.restoration_works.non_shrink_grout_product_used.trim(),
        epoxy_ab_used: form.superstructure.restoration_works.epoxy_ab_used.trim(),
      },
    },
    substructure: {
      concrete_core_extraction: {
        number_of_foundation_locations:
          form.substructure.concrete_core_extraction.number_of_foundation_locations,
        number_of_foundation_cores_extracted:
          form.substructure.concrete_core_extraction.number_of_foundation_cores_extracted,
      },
    },
    signature: {
      prepared_by: form.signature.prepared_by.trim(),
      prepared_by_role: form.signature.prepared_by_role.trim(),
    },
  }
}

async function uploadGroupItem(
  currentSessionId: string,
  groupName: PhotoGroupName,
  item: UploadItem,
): Promise<void> {
  if (item.uploadedImage) {
    item.status = 'uploaded'
    item.message = 'Uploaded'
    return
  }

  try {
    item.status = 'compressing'
    item.message = 'Compressing...'
    const compressedFile = await compressImageForUpload(item.file)

    item.status = 'uploading'
    item.message = 'Uploading...'
    const uploadResult = await uploadReportImage(currentSessionId, groupName, compressedFile)

    item.uploadedImage = uploadResult.image
    item.status = 'uploaded'
    item.message = 'Uploaded'
  } catch (error) {
    item.status = 'error'
    item.message = normalizeErrorMessage(error)
    throw error
  }
}

async function submitIntake(): Promise<void> {
  if (!canSubmit.value) {
    return
  }

  isSubmitting.value = true
  submitError.value = ''
  submitSuccess.value = ''
  confirmationReady.value = false
  generatedDownloadUrl.value = null

  try {
    if (!sessionId.value) {
      const createdSession = await createReportSession()
      sessionId.value = createdSession.session_id
    }

    if (!sessionId.value) {
      throw new Error('Unable to initialize report session.')
    }

    await saveReportFormFields(sessionId.value, buildFormPayload())

    const uploadJobs: Promise<void>[] = []
    for (const group of PHOTO_GROUPS) {
      for (const item of uploads[group.name]) {
        uploadJobs.push(uploadGroupItem(sessionId.value, group.name, item))
      }
    }

    const uploadResults = await Promise.allSettled(uploadJobs)
    const failedUploads = uploadResults.filter(
      (result): result is PromiseRejectedResult => result.status === 'rejected',
    )

    if (failedUploads.length > 0) {
      throw new Error(
        `${failedUploads.length} photo upload${failedUploads.length === 1 ? '' : 's'} failed. ` +
          'Fix the items marked in red and retry.',
      )
    }

    submitSuccess.value = `Draft saved and photos uploaded. Session ${sessionId.value}.`
    confirmationReady.value = true
    void router.push({ name: 'confirmation' })
  } catch (error) {
    submitError.value = normalizeErrorMessage(error)
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <main class="intake-screen">
    <form class="intake-form" @submit.prevent="submitIntake">
      <header class="intake-hero">
        <p class="intake-hero__kicker">SBS Reportr</p>
        <h1 class="intake-hero__title">Activity Report Intake</h1>
        <p class="intake-hero__subtitle">
          Complete each section in report order before proceeding to confirmation.
        </p>
      </header>

      <section class="form-panel">
        <SectionHeader title="Building Details - Cover page information" />
        <div class="field-grid">
          <label class="field">
            <span class="field__label">Testing Date (Month YYYY)</span>
            <input v-model="form.building_details.testing_date" class="field__input" type="month" />
            <span v-if="fieldErrors.testing_date" class="field__error">{{ fieldErrors.testing_date }}</span>
          </label>

          <label class="field">
            <span class="field__label">Building Name</span>
            <input v-model="form.building_details.building_name" class="field__input" maxlength="200" />
            <span v-if="fieldErrors.building_name" class="field__error">{{ fieldErrors.building_name }}</span>
          </label>

          <label class="field field--full">
            <span class="field__label">Building Location</span>
            <textarea
              v-model="form.building_details.building_location"
              class="field__input field__textarea"
              maxlength="500"
            />
            <span v-if="fieldErrors.building_location" class="field__error">{{ fieldErrors.building_location }}</span>
          </label>

          <label class="field">
            <span class="field__label">Number of Storey</span>
            <input
              v-model.number="form.building_details.number_of_storey"
              class="field__input"
              type="number"
              min="1"
            />
            <span v-if="fieldErrors.number_of_storey" class="field__error">{{ fieldErrors.number_of_storey }}</span>
          </label>
        </div>

        <div class="upload-grid upload-grid--single">
          <ImageUploadField
            :label="photoGroupsByName.building_details_building_photo.label"
            :section="photoGroupsByName.building_details_building_photo.section"
            :min="photoGroupsByName.building_details_building_photo.min"
            :max="photoGroupsByName.building_details_building_photo.max"
            :items="uploads.building_details_building_photo"
            :disabled="isSubmitting"
            :error="photoGroupError(photoGroupsByName.building_details_building_photo)"
            @select="(files) => onFilesSelected(photoGroupsByName.building_details_building_photo, files)"
          />
        </div>
      </section>

      <section class="form-panel">
        <SectionHeader title="B.1 Superstructure - Rebar Scanning Details" />
        <div class="field-grid">
          <label class="field">
            <span class="field__label">Number of rebar scan locations</span>
            <input
              v-model.number="form.superstructure.rebar_scanning.number_of_rebar_scan_locations"
              class="field__input"
              type="number"
              min="1"
            />
            <span v-if="fieldErrors.number_of_rebar_scan_locations" class="field__error">
              {{ fieldErrors.number_of_rebar_scan_locations }}
            </span>
          </label>
        </div>

        <div class="upload-grid upload-grid--single">
          <ImageUploadField
            :label="photoGroupsByName.superstructure_rebar_scanning_photos.label"
            :section="photoGroupsByName.superstructure_rebar_scanning_photos.section"
            :min="photoGroupsByName.superstructure_rebar_scanning_photos.min"
            :max="photoGroupsByName.superstructure_rebar_scanning_photos.max"
            :items="uploads.superstructure_rebar_scanning_photos"
            :disabled="isSubmitting"
            :error="photoGroupError(photoGroupsByName.superstructure_rebar_scanning_photos)"
            @select="(files) => onFilesSelected(photoGroupsByName.superstructure_rebar_scanning_photos, files)"
          />
        </div>
      </section>

      <section class="form-panel">
        <SectionHeader title="B.2 Superstructure - Rebound Hammer Test Details" />
        <div class="field-grid">
          <label class="field">
            <span class="field__label">Number of rebound hammer test locations</span>
            <input
              v-model.number="form.superstructure.rebound_hammer_test.number_of_rebound_hammer_test_locations"
              class="field__input"
              type="number"
              min="1"
            />
            <span v-if="fieldErrors.number_of_rebound_hammer_test_locations" class="field__error">
              {{ fieldErrors.number_of_rebound_hammer_test_locations }}
            </span>
          </label>
        </div>

        <div class="upload-grid upload-grid--single">
          <ImageUploadField
            :label="photoGroupsByName.superstructure_rebound_hammer_test_photos.label"
            :section="photoGroupsByName.superstructure_rebound_hammer_test_photos.section"
            :min="photoGroupsByName.superstructure_rebound_hammer_test_photos.min"
            :max="photoGroupsByName.superstructure_rebound_hammer_test_photos.max"
            :items="uploads.superstructure_rebound_hammer_test_photos"
            :disabled="isSubmitting"
            :error="photoGroupError(photoGroupsByName.superstructure_rebound_hammer_test_photos)"
            @select="(files) => onFilesSelected(photoGroupsByName.superstructure_rebound_hammer_test_photos, files)"
          />
        </div>
      </section>

      <section class="form-panel">
        <SectionHeader title="B.3 Superstructure - Concrete Core Extraction Details" />
        <div class="field-grid">
          <label class="field">
            <span class="field__label">Number of coring locations</span>
            <input
              v-model.number="form.superstructure.concrete_core_extraction.number_of_coring_locations"
              class="field__input"
              type="number"
              min="1"
            />
            <span v-if="fieldErrors.number_of_coring_locations" class="field__error">
              {{ fieldErrors.number_of_coring_locations }}
            </span>
          </label>
        </div>

        <div class="upload-grid upload-grid--pair">
          <ImageUploadField
            :label="photoGroupsByName.superstructure_concrete_coring_photos.label"
            :section="photoGroupsByName.superstructure_concrete_coring_photos.section"
            :min="photoGroupsByName.superstructure_concrete_coring_photos.min"
            :max="photoGroupsByName.superstructure_concrete_coring_photos.max"
            :items="uploads.superstructure_concrete_coring_photos"
            :disabled="isSubmitting"
            :error="photoGroupError(photoGroupsByName.superstructure_concrete_coring_photos)"
            @select="(files) => onFilesSelected(photoGroupsByName.superstructure_concrete_coring_photos, files)"
          />
          <ImageUploadField
            :label="photoGroupsByName.superstructure_core_samples_family_pic.label"
            :section="photoGroupsByName.superstructure_core_samples_family_pic.section"
            :min="photoGroupsByName.superstructure_core_samples_family_pic.min"
            :max="photoGroupsByName.superstructure_core_samples_family_pic.max"
            :items="uploads.superstructure_core_samples_family_pic"
            :disabled="isSubmitting"
            :error="photoGroupError(photoGroupsByName.superstructure_core_samples_family_pic)"
            @select="(files) => onFilesSelected(photoGroupsByName.superstructure_core_samples_family_pic, files)"
          />
        </div>
      </section>

      <section class="form-panel">
        <SectionHeader title="B.4 Superstructure - Rebar Extraction Details" />
        <div class="field-grid">
          <label class="field">
            <span class="field__label">Number of rebar samples</span>
            <input
              v-model.number="form.superstructure.rebar_extraction.number_of_rebar_samples_extracted"
              class="field__input"
              type="number"
              min="1"
            />
            <span v-if="fieldErrors.number_of_rebar_samples_extracted" class="field__error">
              {{ fieldErrors.number_of_rebar_samples_extracted }}
            </span>
          </label>
        </div>

        <div class="upload-grid upload-grid--pair">
          <ImageUploadField
            :label="photoGroupsByName.superstructure_rebar_extraction_photos.label"
            :section="photoGroupsByName.superstructure_rebar_extraction_photos.section"
            :min="photoGroupsByName.superstructure_rebar_extraction_photos.min"
            :max="photoGroupsByName.superstructure_rebar_extraction_photos.max"
            :items="uploads.superstructure_rebar_extraction_photos"
            :disabled="isSubmitting"
            :error="photoGroupError(photoGroupsByName.superstructure_rebar_extraction_photos)"
            @select="(files) => onFilesSelected(photoGroupsByName.superstructure_rebar_extraction_photos, files)"
          />
          <ImageUploadField
            :label="photoGroupsByName.superstructure_rebar_samples_family_pic.label"
            :section="photoGroupsByName.superstructure_rebar_samples_family_pic.section"
            :min="photoGroupsByName.superstructure_rebar_samples_family_pic.min"
            :max="photoGroupsByName.superstructure_rebar_samples_family_pic.max"
            :items="uploads.superstructure_rebar_samples_family_pic"
            :disabled="isSubmitting"
            :error="photoGroupError(photoGroupsByName.superstructure_rebar_samples_family_pic)"
            @select="(files) => onFilesSelected(photoGroupsByName.superstructure_rebar_samples_family_pic, files)"
          />
        </div>
      </section>

      <section class="form-panel">
        <SectionHeader title="B.5 Superstructure - Chipping of Existing Slab Details" />
        <div class="upload-grid upload-grid--single">
          <ImageUploadField
            :label="photoGroupsByName.superstructure_chipping_of_slab_photos.label"
            :section="photoGroupsByName.superstructure_chipping_of_slab_photos.section"
            :min="photoGroupsByName.superstructure_chipping_of_slab_photos.min"
            :max="photoGroupsByName.superstructure_chipping_of_slab_photos.max"
            :items="uploads.superstructure_chipping_of_slab_photos"
            :disabled="isSubmitting"
            :error="photoGroupError(photoGroupsByName.superstructure_chipping_of_slab_photos)"
            @select="(files) => onFilesSelected(photoGroupsByName.superstructure_chipping_of_slab_photos, files)"
          />
        </div>
      </section>

      <section class="form-panel">
        <SectionHeader title="B.6 Superstructure - Restoration Works Details" />
        <div class="field-grid">
          <label class="field">
            <span class="field__label">Non-shrink grout product used</span>
            <input
              v-model="form.superstructure.restoration_works.non_shrink_grout_product_used"
              class="field__input"
              maxlength="200"
            />
            <span v-if="fieldErrors.non_shrink_grout_product_used" class="field__error">
              {{ fieldErrors.non_shrink_grout_product_used }}
            </span>
          </label>

          <label class="field">
            <span class="field__label">Epoxy A&amp;B used?</span>
            <input
              v-model="form.superstructure.restoration_works.epoxy_ab_used"
              class="field__input"
              maxlength="200"
            />
            <span v-if="fieldErrors.epoxy_ab_used" class="field__error">{{ fieldErrors.epoxy_ab_used }}</span>
          </label>
        </div>

        <div class="upload-grid upload-grid--single">
          <ImageUploadField
            :label="photoGroupsByName.superstructure_restoration_photos.label"
            :section="photoGroupsByName.superstructure_restoration_photos.section"
            :min="photoGroupsByName.superstructure_restoration_photos.min"
            :max="photoGroupsByName.superstructure_restoration_photos.max"
            :items="uploads.superstructure_restoration_photos"
            :disabled="isSubmitting"
            :error="photoGroupError(photoGroupsByName.superstructure_restoration_photos)"
            @select="(files) => onFilesSelected(photoGroupsByName.superstructure_restoration_photos, files)"
          />
        </div>
      </section>

      <section class="form-panel">
        <SectionHeader title="C.1 Substructure - Concrete Core Extraction Details" />
        <div class="field-grid">
          <label class="field">
            <span class="field__label">Number of selected foundation locations</span>
            <input
              v-model.number="form.substructure.concrete_core_extraction.number_of_foundation_locations"
              class="field__input"
              type="number"
              min="1"
            />
            <span v-if="fieldErrors.number_of_foundation_locations" class="field__error">
              {{ fieldErrors.number_of_foundation_locations }}
            </span>
          </label>

          <label class="field">
            <span class="field__label">Number of extracted cores</span>
            <input
              v-model.number="form.substructure.concrete_core_extraction.number_of_foundation_cores_extracted"
              class="field__input"
              type="number"
              min="1"
            />
            <span v-if="fieldErrors.number_of_foundation_cores_extracted" class="field__error">
              {{ fieldErrors.number_of_foundation_cores_extracted }}
            </span>
          </label>
        </div>

        <div class="upload-grid upload-grid--single">
          <ImageUploadField
            :label="photoGroupsByName.substructure_coring_for_foundation_photos.label"
            :section="photoGroupsByName.substructure_coring_for_foundation_photos.section"
            :min="photoGroupsByName.substructure_coring_for_foundation_photos.min"
            :max="photoGroupsByName.substructure_coring_for_foundation_photos.max"
            :items="uploads.substructure_coring_for_foundation_photos"
            :disabled="isSubmitting"
            :error="photoGroupError(photoGroupsByName.substructure_coring_for_foundation_photos)"
            @select="(files) => onFilesSelected(photoGroupsByName.substructure_coring_for_foundation_photos, files)"
          />
        </div>
      </section>

      <section class="form-panel">
        <SectionHeader title="C.2 Substructure - Rebar Scanning Details" />
        <div class="upload-grid upload-grid--single">
          <ImageUploadField
            :label="photoGroupsByName.substructure_rebar_scanning_for_foundation_photos.label"
            :section="photoGroupsByName.substructure_rebar_scanning_for_foundation_photos.section"
            :min="photoGroupsByName.substructure_rebar_scanning_for_foundation_photos.min"
            :max="photoGroupsByName.substructure_rebar_scanning_for_foundation_photos.max"
            :items="uploads.substructure_rebar_scanning_for_foundation_photos"
            :disabled="isSubmitting"
            :error="photoGroupError(photoGroupsByName.substructure_rebar_scanning_for_foundation_photos)"
            @select="(files) => onFilesSelected(photoGroupsByName.substructure_rebar_scanning_for_foundation_photos, files)"
          />
        </div>
      </section>

      <section class="form-panel">
        <SectionHeader title="C.3 Substructure - Restoration for Coring Works, Backfilling, and Compaction Details" />
        <div class="upload-grid upload-grid--single">
          <ImageUploadField
            :label="photoGroupsByName.substructure_restoration_backfilling_compaction_photos.label"
            :section="photoGroupsByName.substructure_restoration_backfilling_compaction_photos.section"
            :min="photoGroupsByName.substructure_restoration_backfilling_compaction_photos.min"
            :max="photoGroupsByName.substructure_restoration_backfilling_compaction_photos.max"
            :items="uploads.substructure_restoration_backfilling_compaction_photos"
            :disabled="isSubmitting"
            :error="photoGroupError(photoGroupsByName.substructure_restoration_backfilling_compaction_photos)"
            @select="(files) => onFilesSelected(photoGroupsByName.substructure_restoration_backfilling_compaction_photos, files)"
          />
        </div>
      </section>

      <section class="form-panel">
        <SectionHeader title="Signature - Prepared by" />
        <div class="field-grid field-grid--signature">
          <label class="field">
            <span class="field__label">Prepared by</span>
            <input v-model="form.signature.prepared_by" class="field__input" maxlength="100" />
            <span v-if="fieldErrors.prepared_by" class="field__error">{{ fieldErrors.prepared_by }}</span>
          </label>

          <label class="field">
            <span class="field__label">Prepared by role</span>
            <input v-model="form.signature.prepared_by_role" class="field__input" maxlength="100" />
            <span v-if="fieldErrors.prepared_by_role" class="field__error">{{ fieldErrors.prepared_by_role }}</span>
          </label>
        </div>
      </section>

      <footer class="form-actions">
        <button class="btn btn--primary" type="submit" :disabled="!canSubmit">
          {{ isSubmitting ? 'Saving draft and uploading photos...' : 'Continue to Confirmation' }}
        </button>
        <p class="form-summary">
          Continue unlocks only when all required fields and photo groups are valid.
        </p>
        <p v-if="submitError" class="form-summary form-summary--error">{{ submitError }}</p>
        <p v-if="submitSuccess" class="form-summary form-summary--success">{{ submitSuccess }}</p>
        <p v-if="sessionId" class="form-summary form-summary--mono">Session ID: {{ sessionId }}</p>
      </footer>
    </form>
  </main>
</template>

<style scoped>
.intake-screen {
  padding: 0 1rem 3rem;
}

.intake-form {
  width: min(1200px, 100%);
  margin: 0 auto;
  display: grid;
  gap: 1.25rem;
}

.intake-hero {
  padding: 1.15rem;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--paper);
}

.intake-hero__kicker {
  margin: 0;
  font: 700 0.72rem/1.4 var(--font-mono);
  color: var(--orange);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.intake-hero__title {
  margin: 0.2rem 0 0.45rem;
  font: 700 1.75rem/1.1 var(--font-display);
  color: var(--navy);
  text-transform: uppercase;
  letter-spacing: 0.02em;
}

.intake-hero__subtitle {
  margin: 0;
  color: var(--muted);
}

.form-panel {
  display: grid;
  gap: 0.85rem;
  padding: 1rem;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--paper);
}

.field-grid {
  display: grid;
  gap: 0.85rem;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  align-items: start;
}

.field-grid--signature {
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}

.field {
  display: grid;
  gap: 0.35rem;
  align-content: start;
}

.field--full {
  grid-column: 1 / -1;
}

.field__label {
  font: 600 0.83rem/1.3 var(--font-body);
  color: var(--ink);
}

.field__input {
  width: 100%;
  padding: 0.58rem 0.65rem;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #fff;
  color: var(--ink);
  font: 500 0.95rem/1.4 var(--font-body);
}

.field__input:focus {
  outline: 2px solid color-mix(in srgb, var(--orange) 35%, transparent);
  border-color: var(--orange);
}

.field__textarea {
  min-height: 90px;
  resize: vertical;
}

.field__error {
  color: #b42318;
  font: 500 0.76rem/1.3 var(--font-body);
}

.upload-grid {
  display: grid;
  gap: 0.75rem;
}

.upload-grid--single {
  grid-template-columns: minmax(260px, 420px);
}

.upload-grid--pair {
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
}

.form-actions {
  display: grid;
  gap: 0.5rem;
  padding: 1.2rem;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--paper);
}

.btn {
  border: 0;
  border-radius: 10px;
  padding: 0.75rem 1rem;
  font: 700 0.95rem/1 var(--font-body);
  cursor: pointer;
}

.btn--primary {
  color: #fff;
  background: linear-gradient(95deg, var(--orange) 0%, #ff6d2f 100%);
}

.btn--primary:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.form-summary {
  margin: 0;
  color: var(--muted);
  font-size: 0.86rem;
}

.form-summary--warning {
  color: #7a2e0a;
}

.form-summary--error {
  color: #b42318;
}

.form-summary--success {
  color: #067647;
}

.form-summary--mono {
  font-family: var(--font-mono);
  color: var(--navy);
}

@media (max-width: 700px) {
  .intake-screen {
    padding: 0 0.75rem 2rem;
  }

  .intake-hero__title {
    font-size: 1.55rem;
  }

  .upload-grid--single {
    grid-template-columns: 1fr;
  }
}
</style>
