<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../services/api.js'

const router = useRouter()

const nombre = ref('')
const apellido = ref('')
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleRegister() {
  error.value = ''
  loading.value = true
  const res = await api.post('/auth/register', {
    nombre: nombre.value,
    apellido: apellido.value,
    email: email.value,
    password: password.value,
  })
  loading.value = false

  if (!res.ok) {
    error.value = res.error?.detail || 'Error al registrar'
    return
  }

  router.push('/login')
}
</script>

<template>
  <div class="auth-wrapper">
    <div class="card auth-card">
      <div class="card-body">
        <div class="auth-logo">
          <i class="bi bi-person-plus-fill"></i>
        </div>
        <h3 class="text-center mb-1">Crear cuenta</h3>
        <p class="text-center text-muted mb-4">Registrate en SOA 2026</p>

        <div v-if="error" class="alert alert-danger">
          <i class="bi bi-exclamation-triangle me-2"></i>{{ error }}
        </div>

        <form @submit.prevent="handleRegister">
          <div class="row g-2 mb-3">
            <div class="col">
              <label class="form-label">Nombre</label>
              <input v-model="nombre" type="text" class="form-control" placeholder="Juan" required />
            </div>
            <div class="col">
              <label class="form-label">Apellido</label>
              <input v-model="apellido" type="text" class="form-control" placeholder="Perez" required />
            </div>
          </div>
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
            <i class="bi bi-person-plus me-1"></i>
            {{ loading ? 'Creando...' : 'Registrarse' }}
          </button>
        </form>
        <p class="text-center mt-4 mb-0">
          <span class="text-muted">Ya tenes cuenta?</span>
          <router-link to="/login" class="ms-1 fw-bold">Iniciar sesion</router-link>
        </p>
      </div>
    </div>
  </div>
</template>
