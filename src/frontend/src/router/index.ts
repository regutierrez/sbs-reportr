import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'intake',
      component: () => import('@/screens/IntakeFormScreen.vue'),
    },
  ],
})

export default router
