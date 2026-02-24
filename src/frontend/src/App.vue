<script setup lang="ts">
import { RouterView } from 'vue-router'

const currentYear = new Date().getFullYear()
</script>

<template>
  <div class="app-shell">
    <header class="app-header">
      <img src="/asset-80.svg" alt="SBSTRUC" class="app-header__logo" />
      <p class="app-header__subtitle">Activity Report Builder</p>
    </header>

    <div class="app-content">
      <RouterView />
    </div>

    <footer class="app-footer">
      <span class="app-footer__brand">
        <img src="/asset-79.svg" alt="" class="app-footer__icon" />
        <span>SBTRUC</span>
      </span>
      <span class="app-footer__copy">&copy; {{ currentYear }} SBSTRUC</span>
    </footer>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  display: grid;
  place-items: center;
  gap: 0.2rem;
  padding: 1.15rem 1rem 0.35rem;
}

.app-header__logo {
  width: min(300px, 72vw);
  height: auto;
}

.app-header__subtitle {
  margin: 0;
  font: 700 0.7rem/1.3 var(--font-mono);
  letter-spacing: 0.12em;
  color: var(--muted);
  text-transform: uppercase;
}

.app-content {
  flex: 1;
}

.app-footer {
  width: min(1200px, calc(100% - 2rem));
  margin: 0 auto 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-top: 1px solid var(--line);
  padding: 0.9rem 0 0;
  font-family: var(--font-mono);
  font-size: 0.72rem;
  color: var(--muted);
}

.app-footer__brand {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
}

.app-footer__icon {
  width: 17px;
  height: 17px;
  opacity: 0.58;
}

.app-footer__copy {
  color: var(--navy);
  font-weight: 700;
}

@media (max-width: 700px) {
  .app-header {
    padding-top: 0.85rem;
  }

  .app-footer {
    width: calc(100% - 1.5rem);
    margin-bottom: 0.8rem;
    flex-direction: column;
    gap: 0.4rem;
    text-align: center;
  }
}
</style>
