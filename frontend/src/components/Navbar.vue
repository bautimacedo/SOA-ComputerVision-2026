<script setup>
import { useAuthStore } from '../stores/auth.js'
import { useRouter } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <nav class="navbar navbar-expand-lg navbar-dark navbar-custom">
    <div class="container">
      <router-link class="navbar-brand" to="/">
        <i class="bi bi-eye-fill me-2"></i>SOA 2026
      </router-link>
      <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#nav">
        <span class="navbar-toggler-icon"></span>
      </button>
      <div class="collapse navbar-collapse" id="nav">
        <ul class="navbar-nav me-auto">
          <li class="nav-item">
            <router-link class="nav-link" active-class="active" to="/">
              <i class="bi bi-cpu"></i>Deteccion
            </router-link>
          </li>
          <li class="nav-item">
            <router-link class="nav-link" active-class="active" to="/search">
              <i class="bi bi-search"></i>Busqueda
            </router-link>
          </li>
          <li class="nav-item">
            <router-link class="nav-link" active-class="active" to="/persons">
              <i class="bi bi-people"></i>Personas
            </router-link>
          </li>
          <li class="nav-item">
            <router-link class="nav-link" active-class="active" to="/recognition">
              <i class="bi bi-person-bounding-box"></i>Reconocimiento
            </router-link>
          </li>
        </ul>
        <div class="d-flex align-items-center gap-2" v-if="auth.isLoggedIn">
          <span class="user-badge text-white">
            <i class="bi bi-person-circle me-1"></i>{{ auth.person?.nombre }} {{ auth.person?.apellido }}
          </span>
          <button class="btn btn-outline-light btn-sm" @click="handleLogout">
            <i class="bi bi-box-arrow-right me-1"></i>Salir
          </button>
        </div>
      </div>
    </div>
  </nav>
</template>
