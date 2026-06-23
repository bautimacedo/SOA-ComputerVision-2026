<script setup>
import { ref, onMounted } from 'vue'
import api from '../services/api.js'

const models = ref([])
const selectedModel = ref('')
const imageFile = ref(null)
const imagePreview = ref(null)
const lat = ref('-34.6037')
const lon = ref('-58.3816')
const extraMeta = ref('')
const result = ref(null)
const error = ref('')
const loading = ref(false)
const loadingModels = ref(true)

onMounted(async () => {
  const res = await api.get('/models')
  loadingModels.value = false
  if (res.ok) {
    models.value = res.data
    if (res.data.length > 0) selectedModel.value = res.data[0]
  }
})

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

async function handleDetect() {
  error.value = ''
  result.value = null

  if (!imageFile.value) { error.value = 'Selecciona una imagen'; return }
  if (!lat.value || !lon.value) { error.value = 'Latitud y longitud son obligatorios'; return }

  let metaObj = { lat: parseFloat(lat.value), lon: parseFloat(lon.value) }
  if (extraMeta.value) {
    try {
      const extra = JSON.parse(extraMeta.value)
      metaObj = { ...metaObj, ...extra }
    } catch {
      error.value = 'Metadata extra debe ser JSON valido'
      return
    }
  }

  const formData = new FormData()
  formData.append('image', imageFile.value)
  formData.append('model_id', selectedModel.value)
  formData.append('metadata', JSON.stringify(metaObj))

  loading.value = true
  const res = await api.postForm('/detections', formData)
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
    <h2><i class="bi bi-cpu"></i> Deteccion de objetos</h2>
    <p>Subi una imagen, selecciona un modelo YOLO y ejecuta la deteccion.</p>
  </div>

  <div class="row g-4">
    <div class="col-lg-6">
      <div class="card">
        <div class="card-header header-primary">
          <i class="bi bi-upload me-2"></i>Configuracion
        </div>
        <div class="card-body">
          <div v-if="error" class="alert alert-danger">
            <i class="bi bi-exclamation-triangle me-2"></i>{{ error }}
          </div>

          <div class="mb-3">
            <label class="form-label">Modelo</label>
            <select v-model="selectedModel" class="form-select" :disabled="loadingModels">
              <option v-if="loadingModels" disabled>Cargando modelos...</option>
              <option v-for="m in models" :key="m" :value="m">{{ m }}</option>
            </select>
          </div>

          <div class="mb-3">
            <label class="form-label">Imagen</label>
            <input type="file" class="form-control" accept="image/*" @change="onFileChange" />
            <div v-if="imagePreview" class="mt-2 text-center">
              <img :src="imagePreview" class="img-fluid rounded" style="max-height: 200px" />
            </div>
          </div>

          <div class="row mb-3">
            <div class="col">
              <label class="form-label">Latitud</label>
              <input v-model="lat" type="number" step="any" class="form-control" />
            </div>
            <div class="col">
              <label class="form-label">Longitud</label>
              <input v-model="lon" type="number" step="any" class="form-control" />
            </div>
          </div>

          <div class="mb-3">
            <label class="form-label">Metadata extra (JSON, opcional)</label>
            <input v-model="extraMeta" type="text" class="form-control" placeholder='{"camara":"cam_01"}' />
          </div>

          <button class="btn btn-primary w-100" @click="handleDetect" :disabled="loading">
            <i class="bi bi-play-fill me-1"></i>
            {{ loading ? 'Procesando...' : 'Ejecutar deteccion' }}
          </button>
        </div>
      </div>
    </div>

    <div class="col-lg-6" v-if="result">
      <div class="card">
        <div class="card-header header-success">
          <i class="bi bi-check-circle me-2"></i>Resultado
        </div>
        <div class="card-body">
          <div class="row mb-3">
            <div class="col-6">
              <div class="stat-label">Frame ID</div>
              <code class="small">{{ result.frameId }}</code>
            </div>
            <div class="col-6">
              <div class="stat-label">Modelo</div>
              <span class="badge bg-primary">{{ result.modelId }}</span>
            </div>
          </div>

          <div class="d-flex align-items-center mb-3 gap-3">
            <div class="text-center">
              <div class="stat-number text-primary">{{ result.detections.length }}</div>
              <div class="stat-label">Objetos detectados</div>
            </div>
          </div>

          <table class="table table-hover" v-if="result.detections.length > 0">
            <thead>
              <tr>
                <th>Clase</th>
                <th>Confianza</th>
                <th>Bounding Box</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(d, i) in result.detections" :key="i">
                <td><span class="badge bg-primary">{{ d.class }}</span></td>
                <td>
                  <div class="d-flex align-items-center gap-2">
                    <div class="progress flex-grow-1" style="height: 8px">
                      <div class="progress-bar bg-success" :style="{ width: (d.confidence * 100) + '%' }"></div>
                    </div>
                    <small class="fw-bold">{{ (d.confidence * 100).toFixed(1) }}%</small>
                  </div>
                </td>
                <td><code class="small">{{ d.bbox?.map(v => v.toFixed(3)).join(', ') }}</code></td>
              </tr>
            </tbody>
          </table>
          <div v-else class="alert alert-info">
            <i class="bi bi-info-circle me-2"></i>No se detectaron objetos.
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
