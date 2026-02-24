<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { ApiError, generateReport, resolveApiUrl } from '@/api'
import SectionHeader from '@/components/SectionHeader.vue'
import { PHOTO_GROUPS } from '@/constants/photo-groups'
import { useReportIntakeDraft } from '@/composables/use-report-intake-draft'

const router = useRouter()
const { confirmationReady, form, generatedDownloadUrl, sessionId, uploads } = useReportIntakeDraft()

const isGenerating = ref(false)
const generateError = ref('')
const generateSuccess = ref('')

const photoSummary = computed(() => {
  return PHOTO_GROUPS.map((group) => {
    const uploaded = uploads[group.name].filter((item) => item.uploadedImage !== null).length

    return {
      ...group,
      uploaded,
      complete: uploaded >= group.min,
    }
  })
})

const canContinue = computed(() => {
  return confirmationReady.value && !!sessionId.value && !isGenerating.value
})

const canRedownload = computed(() => {
  return !!generatedDownloadUrl.value
})

onMounted(() => {
  if (!confirmationReady.value || !sessionId.value) {
    void router.replace({ name: 'intake' })
  }
})

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

  return 'Unexpected error while generating report.'
}

async function continueToGenerate(): Promise<void> {
  if (!sessionId.value) {
    return
  }

  isGenerating.value = true
  generateError.value = ''
  generateSuccess.value = ''

  try {
    const generated = await generateReport(sessionId.value)
    generatedDownloadUrl.value = generated.download_url
    generateSuccess.value = 'Report generated. A new tab was opened for download.'
    window.open(resolveApiUrl(generated.download_url), '_blank', 'noopener')
  } catch (error) {
    generateError.value = normalizeErrorMessage(error)
  } finally {
    isGenerating.value = false
  }
}

function redownloadReport(): void {
  if (!generatedDownloadUrl.value) {
    return
  }

  window.open(resolveApiUrl(generatedDownloadUrl.value), '_blank', 'noopener')
}

function revertToForm(): void {
  generateError.value = ''
  generateSuccess.value = ''
  void router.push({ name: 'intake' })
}
</script>

<template>
  <main class="confirmation-screen">
    <div class="confirmation-layout">
      <header class="confirmation-hero">
        <p class="confirmation-hero__kicker">SBS Reportr</p>
        <h1 class="confirmation-hero__title">Confirmation</h1>
        <p class="confirmation-hero__subtitle">
          Review the prepared intake data before generating the final report PDF.
        </p>
      </header>

      <section class="confirmation-panel">
        <SectionHeader title="Building Snapshot" subtitle="Cover page values" />
        <dl class="data-grid">
          <div class="data-grid__item">
            <dt>Testing Date</dt>
            <dd>{{ form.building_details.testing_date }}</dd>
          </div>
          <div class="data-grid__item">
            <dt>Building Name</dt>
            <dd>{{ form.building_details.building_name }}</dd>
          </div>
          <div class="data-grid__item data-grid__item--full">
            <dt>Building Location</dt>
            <dd>{{ form.building_details.building_location }}</dd>
          </div>
          <div class="data-grid__item">
            <dt>Number of Storey</dt>
            <dd>{{ form.building_details.number_of_storey }}</dd>
          </div>
        </dl>
      </section>

      <section class="confirmation-panel">
        <SectionHeader title="Key Counts" subtitle="Superstructure and substructure entries" />
        <dl class="data-grid">
          <div class="data-grid__item">
            <dt>Rebar Scan Locations</dt>
            <dd>{{ form.superstructure.rebar_scanning.number_of_rebar_scan_locations }}</dd>
          </div>
          <div class="data-grid__item">
            <dt>Rebound Hammer Test Locations</dt>
            <dd>{{ form.superstructure.rebound_hammer_test.number_of_rebound_hammer_test_locations }}</dd>
          </div>
          <div class="data-grid__item">
            <dt>Coring Locations</dt>
            <dd>{{ form.superstructure.concrete_core_extraction.number_of_coring_locations }}</dd>
          </div>
          <div class="data-grid__item">
            <dt>Rebar Samples Extracted</dt>
            <dd>{{ form.superstructure.rebar_extraction.number_of_rebar_samples_extracted }}</dd>
          </div>
          <div class="data-grid__item">
            <dt>Foundation Locations</dt>
            <dd>{{ form.substructure.concrete_core_extraction.number_of_foundation_locations }}</dd>
          </div>
          <div class="data-grid__item">
            <dt>Foundation Cores Extracted</dt>
            <dd>{{ form.substructure.concrete_core_extraction.number_of_foundation_cores_extracted }}</dd>
          </div>
          <div class="data-grid__item">
            <dt>Prepared By</dt>
            <dd>{{ form.signature.prepared_by }}</dd>
          </div>
          <div class="data-grid__item">
            <dt>Role</dt>
            <dd>{{ form.signature.prepared_by_role }}</dd>
          </div>
        </dl>
      </section>

      <section class="confirmation-panel">
        <SectionHeader title="Photo Coverage" subtitle="Required groups uploaded" />
        <ul class="photo-summary-list">
          <li v-for="group in photoSummary" :key="group.name" class="photo-summary-item">
            <div>
              <p class="photo-summary-item__label">{{ group.label }}</p>
              <p class="photo-summary-item__section">{{ group.section }}</p>
            </div>
            <p class="photo-summary-item__count" :data-complete="group.complete">
              {{ group.uploaded }} / {{ group.min }} min
            </p>
          </li>
        </ul>
      </section>

      <footer class="confirmation-actions">
        <p class="confirmation-actions__session">Session ID: {{ sessionId }}</p>
        <div class="confirmation-actions__buttons">
          <button class="btn btn--secondary" type="button" @click="revertToForm">Revert</button>
          <button
            class="btn btn--secondary"
            type="button"
            :disabled="!canRedownload"
            @click="redownloadReport"
          >
            Download Again
          </button>
          <button class="btn btn--primary" type="button" :disabled="!canContinue" @click="continueToGenerate">
            {{ isGenerating ? 'Generating...' : 'Continue and Generate PDF' }}
          </button>
        </div>
        <p v-if="generateError" class="confirmation-actions__message confirmation-actions__message--error">
          {{ generateError }}
        </p>
        <p v-if="generateSuccess" class="confirmation-actions__message confirmation-actions__message--success">
          {{ generateSuccess }}
        </p>
        <p v-if="generatedDownloadUrl" class="confirmation-actions__message confirmation-actions__message--mono">
          Download URL: {{ generatedDownloadUrl }}
        </p>
      </footer>
    </div>
  </main>
</template>

<style scoped>
.confirmation-screen {
  padding: 0.75rem 1rem 3rem;
  background:
    radial-gradient(circle at 8% 5%, color-mix(in srgb, var(--navy) 10%, transparent), transparent 32%),
    linear-gradient(120deg, #edf3ff 0%, #f7f9fc 48%, #eef5ff 100%);
}

.confirmation-layout {
  width: min(1000px, 100%);
  margin: 0 auto;
  display: grid;
  gap: 1rem;
}

.confirmation-hero,
.confirmation-panel,
.confirmation-actions {
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--paper);
}

.confirmation-hero,
.confirmation-actions {
  padding: 1.2rem;
}

.confirmation-panel {
  padding: 1rem;
}

.confirmation-hero__kicker {
  margin: 0;
  font: 700 0.75rem/1.3 var(--font-mono);
  text-transform: uppercase;
  color: var(--orange);
  letter-spacing: 0.08em;
}

.confirmation-hero__title {
  margin: 0.2rem 0 0.45rem;
  font: 700 1.9rem/1.1 var(--font-display);
  color: var(--navy);
  text-transform: uppercase;
}

.confirmation-hero__subtitle {
  margin: 0;
  color: var(--muted);
}

.data-grid {
  margin: 0;
  display: grid;
  gap: 0.6rem;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.data-grid__item {
  margin: 0;
  padding: 0.65rem;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #fff;
}

.data-grid__item--full {
  grid-column: 1 / -1;
}

.data-grid__item dt {
  color: var(--muted);
  font: 600 0.75rem/1.2 var(--font-mono);
  text-transform: uppercase;
}

.data-grid__item dd {
  margin: 0.35rem 0 0;
  color: var(--ink);
  font: 600 0.95rem/1.25 var(--font-body);
}

.photo-summary-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 0.45rem;
}

.photo-summary-item {
  padding: 0.65rem;
  border: 1px solid var(--line);
  border-radius: 10px;
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  align-items: center;
}

.photo-summary-item__label,
.photo-summary-item__section,
.photo-summary-item__count {
  margin: 0;
}

.photo-summary-item__label {
  color: var(--ink);
  font-weight: 600;
}

.photo-summary-item__section {
  color: var(--muted);
  font-size: 0.8rem;
}

.photo-summary-item__count {
  font: 700 0.78rem/1 var(--font-mono);
  color: #067647;
}

.photo-summary-item__count[data-complete='false'] {
  color: #b42318;
}

.confirmation-actions {
  display: grid;
  gap: 0.55rem;
}

.confirmation-actions__session {
  margin: 0;
  color: var(--navy);
  font: 600 0.78rem/1.3 var(--font-mono);
}

.confirmation-actions__buttons {
  display: flex;
  gap: 0.6rem;
  flex-wrap: wrap;
}

.btn {
  border: 0;
  border-radius: 10px;
  padding: 0.72rem 1rem;
  font: 700 0.92rem/1 var(--font-body);
  cursor: pointer;
}

.btn--primary {
  color: #fff;
  background: linear-gradient(95deg, var(--orange) 0%, #ff6d2f 100%);
}

.btn--secondary {
  color: var(--navy);
  background: #e9eefc;
}

.btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.confirmation-actions__message {
  margin: 0;
  font-size: 0.84rem;
}

.confirmation-actions__message--error {
  color: #b42318;
}

.confirmation-actions__message--success {
  color: #067647;
}

.confirmation-actions__message--mono {
  font-family: var(--font-mono);
  color: var(--muted);
}

@media (max-width: 700px) {
  .confirmation-screen {
    padding: 0.3rem 0.75rem 2rem;
  }

  .confirmation-hero__title {
    font-size: 1.55rem;
  }
}
</style>
