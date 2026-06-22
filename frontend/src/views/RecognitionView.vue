<script setup>
import { ref } from 'vue'
import api from '../services/api.js'

const imageFile = ref(null)
const imagePreview = ref(null)
const threshold = ref('0.8')
const result = ref(null)
const error = ref('')
const loading = ref(false)

function onFileChange(e) {
  const file = e.target.files[0]
  imageFile.value = file
  if (file) {
    const reader = new FileReader()
    reader.onload = (ev) => { imagePreview.value = ev.target.result }
    reader.readAsDataURL(file)
  } else {
    imagePreview.value = null
  }
}

async function handleRecognize() {
  error.value = ''
  result.value = null

  if (!imageFile.value) { error.value = 'Selecciona una imagen'; return }

  const formData = new FormData()
  formData.append('image', imageFile.value)
  formData.append('threshold', threshold.value)

  loading.value = true
  const res = await api.postForm('/face-recognition', formData)
  loading.value = false

  if (!res.ok) {
    error.value = res.error?.detail || 'Error al procesar'
    return
  }
  result.value = res.data
}
</script>

<template>
  <div class="page-header">
    <h2><i class="bi bi-person-bounding-box"></i> Reconocimiento facial</h2>
    <p>Subi una foto y el sistema identifica si la persona esta registrada.</p>
  </div>

  <div class="row g-4">
    <div class="col-lg-5">
      <div class="card">
        <div class="card-header header-primary">
          <i class="bi bi-camera me-2"></i>Imagen a reconocer
        </div>
        <div class="card-body">
          <div v-if="error" class="alert alert-danger">
            <i class="bi bi-exclamation-triangle me-2"></i>{{ error }}
          </div>

          <div class="mb-3">
            <label class="form-label">Imagen</label>
            <input type="file" class="form-control" accept="image/*" @change="onFileChange" />
          </div>

          <div v-if="imagePreview" class="mb-3 text-center">
            <img :src="imagePreview" class="img-fluid rounded shadow-sm" style="max-height: 250px" />
          </div>

          <div class="mb-3">
            <label class="form-label">Threshold</label>
            <div class="d-flex align-items-center gap-3">
              <input v-model="threshold" type="range" class="form-range flex-grow-1" min="0" max="1" step="0.05" />
              <span class="badge bg-primary fs-6">{{ threshold }}</span>
            </div>
            <small class="text-muted">Umbral minimo de confianza para aceptar un reconocimiento</small>
          </div>

          <button class="btn btn-primary w-100" @click="handleRecognize" :disabled="loading">
            <i class="bi bi-person-check me-1"></i>
            {{ loading ? 'Analizando...' : 'Reconocer' }}
          </button>
        </div>
      </div>
    </div>

    <div class="col-lg-7" v-if="result">
      <div class="card" :class="result.personId ? 'result-card-success' : 'result-card-fail'">
        <div class="card-header" :class="result.personId ? 'header-success' : 'header-warning'">
          <i class="bi me-2" :class="result.personId ? 'bi-check-circle-fill' : 'bi-question-circle-fill'"></i>
          {{ result.personId ? 'Persona reconocida' : 'No reconocida' }}
        </div>
        <div class="card-body">
          <div v-if="result.personId" class="d-flex align-items-center mb-4">
            <div class="rounded-circle bg-success text-white d-flex align-items-center justify-content-center" style="width:64px;height:64px;font-size:1.5rem">
              {{ result.nombre?.[0] }}{{ result.apellido?.[0] }}
            </div>
            <div class="ms-3">
              <h3 class="mb-0">{{ result.nombre }} {{ result.apellido }}</h3>
              <code class="text-muted">{{ result.personId }}</code>
            </div>
          </div>
          <div v-else class="mb-4">
            <div class="d-flex align-items-center">
              <div class="rounded-circle bg-warning d-flex align-items-center justify-content-center" style="width:64px;height:64px;font-size:1.8rem">
                <i class="bi bi-question-lg"></i>
              </div>
              <div class="ms-3">
                <h4 class="mb-1">Identidad desconocida</h4>
                <p class="text-muted mb-0">No se encontro una persona que supere el umbral de confianza.</p>
              </div>
            </div>
          </div>

          <div>
            <div class="d-flex justify-content-between mb-1">
              <span class="form-label mb-0">Confianza</span>
              <span class="fw-bold" :class="{
                'text-success': result.confidence >= 0.8,
                'text-warning': result.confidence >= 0.5 && result.confidence < 0.8,
                'text-danger': result.confidence < 0.5,
              }">{{ (result.confidence * 100).toFixed(1) }}%</span>
            </div>
            <div class="progress" style="height: 28px">
              <div
                class="progress-bar"
                :class="{
                  'bg-success': result.confidence >= 0.8,
                  'bg-warning': result.confidence >= 0.5 && result.confidence < 0.8,
                  'bg-danger': result.confidence < 0.5,
                }"
                :style="{ width: (result.confidence * 100) + '%' }"
              >
                {{ (result.confidence * 100).toFixed(1) }}%
              </div>
            </div>
            <div class="d-flex justify-content-between mt-1">
              <small class="text-muted">0%</small>
              <small class="text-muted">Threshold: {{ threshold }}</small>
              <small class="text-muted">100%</small>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
