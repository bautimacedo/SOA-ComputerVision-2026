<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import api from '../services/api.js'

const router = useRouter()
const auth = useAuthStore()

const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  loading.value = true
  const res = await api.post('/auth/login', { email: email.value, password: password.value })
  loading.value = false

  if (!res.ok) {
    error.value = res.error?.detail || 'Error al iniciar sesion'
    return
  }

  auth.setSession(res.data, res.data.person)
  router.push('/')
}
</script>

<template>
  <div class="auth-wrapper">
    <div class="card auth-card">
      <div class="card-body">
        <div class="auth-logo">
          <i class="bi bi-eye-fill"></i>
        </div>
        <h3 class="text-center mb-1">Bienvenido</h3>
        <p class="text-center text-muted mb-4">Inicia sesion en SOA 2026</p>

        <div v-if="error" class="alert alert-danger">
          <i class="bi bi-exclamation-triangle me-2"></i>{{ error }}
        </div>

        <form @submit.prevent="handleLogin">
          <div class="mb-3">
            <label class="form-label">Email</label>
            <div class="input-group">
              <span class="input-group-text"><i class="bi bi-envelope"></i></span>
              <input v-model="email" type="email" class="form-control" placeholder="tu@email.com" required />
            </div>
          </div>
          <div class="mb-4">
            <label class="form-label">Contrasena</label>
            <div class="input-group">
              <span class="input-group-text"><i class="bi bi-lock"></i></span>
              <input v-model="password" type="password" class="form-control" placeholder="********" required />
            </div>
          </div>
          <button type="submit" class="btn btn-primary w-100 py-2" :disabled="loading">
            <i class="bi bi-box-arrow-in-right me-1"></i>
            {{ loading ? 'Cargando...' : 'Ingresar' }}
          </button>
        </form>
        <p class="text-center mt-4 mb-0">
          <span class="text-muted">No tenes cuenta?</span>
          <router-link to="/register" class="ms-1 fw-bold">Crear una</router-link>
        </p>
      </div>
    </div>
  </div>
</template>
