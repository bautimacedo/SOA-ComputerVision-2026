import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import DetectionView from '../views/DetectionView.vue'
import SearchView from '../views/SearchView.vue'
import PersonsView from '../views/PersonsView.vue'
import RecognitionView from '../views/RecognitionView.vue'

const routes = [
  { path: '/login', name: 'Login', component: LoginView, meta: { guest: true } },
  { path: '/register', name: 'Register', component: RegisterView, meta: { guest: true } },
  { path: '/', name: 'Detection', component: DetectionView },
  { path: '/search', name: 'Search', component: SearchView },
  { path: '/persons', name: 'Persons', component: PersonsView },
  { path: '/recognition', name: 'Recognition', component: RecognitionView },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.guest && !auth.isLoggedIn) {
    return { name: 'Login' }
  }
})

export default router
