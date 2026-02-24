<script setup lang="ts">
defineProps<{
  title: string
  subtitle?: string
}>()
</script>

<template>
  <header class="section-bar">
    <h2 class="section-bar__title">{{ title }}</h2>
    <p v-if="subtitle" class="section-bar__subtitle">{{ subtitle }}</p>
  </header>
</template>
