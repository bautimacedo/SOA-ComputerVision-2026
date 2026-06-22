<script setup>
import { ref } from 'vue'
import api from '../services/api.js'

const nombre = ref('')
const apellido = ref('')
const email = ref('')
const extra = ref('')
const createError = ref('')
const createSuccess = ref('')
const createLoading = ref(false)

const searchId = ref('')
const personResult = ref(null)
const searchError = ref('')

const embPersonId = ref('')
const embFiles = ref(null)
const embResult = ref(null)
const embError = ref('')
const embLoading = ref(false)

async function handleCreate() {
  createError.value = ''
  createSuccess.value = ''
  createLoading.value = true

  const body = {
    nombre: nombre.value,
    apellido: apellido.value,
    email: email.value,
  }
  if (extra.value) {
    try {
      body.extra = JSON.parse(extra.value)
    } catch {
      createError.value = 'Extra debe ser JSON valido'
      createLoading.value = false
      return
    }
  }

  const res = await api.post('/persons', body)
  createLoading.value = false

  if (!res.ok) {
    createError.value = res.error?.detail || 'Error al crear persona'
    return
  }
  createSuccess.value = `Persona creada — ID: ${res.data.personId || res.data.id}`
  embPersonId.value = res.data.personId || res.data.id
  nombre.value = ''
  apellido.value = ''
  email.value = ''
  extra.value = ''
}

async function handleSearch() {
  searchError.value = ''
  personResult.value = null
  if (!searchId.value) return

  const res = await api.get(`/persons/${searchId.value}`)
  if (!res.ok) {
    searchError.value = res.error?.detail || 'No encontrada'
    return
  }
  personResult.value = res.data
}

function onEmbFiles(e) {
  embFiles.value = e.target.files
}

async function handleEmbeddings() {
  embError.value = ''
  embResult.value = null

  if (!embPersonId.value) { embError.value = 'Ingresa el ID de la persona'; return }
  if (!embFiles.value || embFiles.value.length === 0) { embError.value = 'Selecciona al menos una imagen'; return }

  const formData = new FormData()
  for (const file of embFiles.value) {
    formData.append('images', file)
  }

  embLoading.value = true
  const res = await api.postForm(`/persons/${embPersonId.value}/embeddings`, formData)
  embLoading.value = false

  if (!res.ok) {
    embError.value = res.error?.detail || 'Error al generar embeddings'
    return
  }
  embResult.value = res.data
}
</script>

<template>
  <div class="page-header">
    <h2><i class="bi bi-people"></i> Gestion de personas</h2>
    <p>Registra personas, busca por ID y genera embeddings faciales a partir de fotos.</p>
  </div>

  <div class="row g-4">
    <!-- Crear persona -->
    <div class="col-lg-4">
      <div class="card h-100">
        <div class="card-header header-primary">
          <i class="bi bi-person-plus me-2"></i>Registrar persona
        </div>
        <div class="card-body">
          <div v-if="createError" class="alert alert-danger py-2">
            <i class="bi bi-exclamation-triangle me-1"></i>{{ createError }}
          </div>
          <div v-if="createSuccess" class="alert alert-success py-2">
            <i class="bi bi-check-circle me-1"></i>{{ createSuccess }}
          </div>
          <form @submit.prevent="handleCreate">
            <div class="mb-2">
              <label class="form-label">Nombre</label>
              <input v-model="nombre" type="text" class="form-control" placeholder="Juan" required />
            </div>
            <div class="mb-2">
              <label class="form-label">Apellido</label>
              <input v-model="apellido" type="text" class="form-control" placeholder="Perez" required />
            </div>
            <div class="mb-2">
              <label class="form-label">Email</label>
              <input v-model="email" type="email" class="form-control" placeholder="juan@mail.com" required />
            </div>
            <div class="mb-3">
              <label class="form-label">Extra (JSON, opcional)</label>
              <input v-model="extra" type="text" class="form-control" placeholder='{"legajo":"12345"}' />
            </div>
            <button type="submit" class="btn btn-primary w-100" :disabled="createLoading">
              <i class="bi bi-plus-circle me-1"></i>
              {{ createLoading ? 'Creando...' : 'Registrar' }}
            </button>
          </form>
        </div>
      </div>
    </div>

    <!-- Buscar persona -->
    <div class="col-lg-4">
      <div class="card h-100">
        <div class="card-header header-info">
          <i class="bi bi-search me-2"></i>Buscar persona
        </div>
        <div class="card-body">
          <div v-if="searchError" class="alert alert-danger py-2">
            <i class="bi bi-exclamation-triangle me-1"></i>{{ searchError }}
          </div>
          <div class="mb-3">
            <label class="form-label">Person ID</label>
            <div class="input-group">
              <input v-model="searchId" type="text" class="form-control" placeholder="UUID" />
              <button class="btn btn-primary" @click="handleSearch">
                <i class="bi bi-search"></i>
              </button>
            </div>
          </div>
          <div v-if="personResult" class="mt-3">
            <div class="d-flex align-items-center mb-3">
              <div class="rounded-circle bg-primary text-white d-flex align-items-center justify-content-center" style="width:48px;height:48px;font-size:1.2rem">
                {{ personResult.nombre?.[0] }}{{ personResult.apellido?.[0] }}
              </div>
              <div class="ms-3">
                <h5 class="mb-0">{{ personResult.nombre }} {{ personResult.apellido }}</h5>
                <small class="text-muted">{{ personResult.email }}</small>
              </div>
            </div>
            <p class="mb-1"><small class="form-label">ID</small></p>
            <code class="small">{{ personResult.personId || personResult.id }}</code>
            <div v-if="personResult.extra" class="mt-2">
              <p class="mb-1"><small class="form-label">Extra</small></p>
              <span v-for="(val, key) in personResult.extra" :key="key" class="badge bg-light text-dark me-1">
                {{ key }}: {{ val }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Generar embeddings -->
    <div class="col-lg-4">
      <div class="card h-100">
        <div class="card-header header-success">
          <i class="bi bi-fingerprint me-2"></i>Generar embeddings
        </div>
        <div class="card-body">
          <div v-if="embError" class="alert alert-danger py-2">
            <i class="bi bi-exclamation-triangle me-1"></i>{{ embError }}
          </div>
          <div class="mb-2">
            <label class="form-label">Person ID</label>
            <input v-model="embPersonId" type="text" class="form-control" placeholder="UUID de la persona" />
          </div>
          <div class="mb-3">
            <label class="form-label">Imagenes</label>
            <input type="file" class="form-control" accept="image/*" multiple @change="onEmbFiles" />
            <small class="text-muted">Una o mas fotos con exactamente un rostro cada una</small>
          </div>
          <button class="btn btn-primary w-100" @click="handleEmbeddings" :disabled="embLoading">
            <i class="bi bi-arrow-repeat me-1"></i>
            {{ embLoading ? 'Procesando...' : 'Generar embeddings' }}
          </button>

          <div v-if="embResult" class="mt-3">
            <div class="row text-center g-2">
              <div class="col-4">
                <div class="stat-number text-primary">{{ embResult.processedImages }}</div>
                <div class="stat-label">Procesadas</div>
              </div>
              <div class="col-4">
                <div class="stat-number text-success">{{ embResult.validEmbeddings }}</div>
                <div class="stat-label">Validas</div>
              </div>
              <div class="col-4">
                <div class="stat-number text-danger">{{ embResult.rejectedImages }}</div>
                <div class="stat-label">Rechazadas</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
