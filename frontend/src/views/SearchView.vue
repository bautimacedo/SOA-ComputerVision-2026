<script setup>
import { ref } from 'vue'
import api from '../services/api.js'

const latMin = ref('-35')
const latMax = ref('-34')
const lonMin = ref('-59')
const lonMax = ref('-58')
const classes = ref('')
const modelId = ref('')
const metadata = ref('')
const results = ref(null)
const error = ref('')
const loading = ref(false)
const previewUrl = ref(null)

async function handleSearch() {
  error.value = ''
  results.value = null

  let params = `lat_min=${latMin.value}&lat_max=${latMax.value}&lon_min=${lonMin.value}&lon_max=${lonMax.value}`

  if (modelId.value) params += `&model_id=${encodeURIComponent(modelId.value)}`
  if (classes.value) {
    classes.value.split(',').map(c => c.trim()).filter(Boolean).forEach(c => {
      params += `&classes=${encodeURIComponent(c)}`
    })
  }
  if (metadata.value) params += `&metadata=${encodeURIComponent(metadata.value)}`

  loading.value = true
  const res = await api.get(`/frames/search?${params}`)
  loading.value = false

  if (!res.ok) {
    error.value = res.error?.detail || 'Error en la busqueda'
    return
  }
  results.value = res.data
}

async function showPreview(frameId) {
  const res = await api.get(`/frames/${frameId}?thumbnail=true`)
  if (res.ok && res.blob) {
    previewUrl.value = URL.createObjectURL(res.blob)
  }
}

function closePreview() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = null
}

const downloadingId = ref(null)

// api.get ya manda el header de Authorization — por eso no se puede usar un
// <a href="..."> directo, hay que traer el blob nosotros y "forzar" la descarga.
async function downloadImage(frameId, thumbnail) {
  downloadingId.value = `${frameId}-${thumbnail}`
  try {
    const path = thumbnail ? `/frames/${frameId}?thumbnail=true` : `/frames/${frameId}`
    const res = await api.get(path)
    if (!res.ok || !res.blob) return

    const url = URL.createObjectURL(res.blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${frameId}${thumbnail ? '_thumb' : ''}.jpg`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } finally {
    downloadingId.value = null
  }
}
</script>

<template>
  <div class="page-header">
    <h2><i class="bi bi-search"></i> Busqueda de fotogramas</h2>
    <p>Filtra fotogramas procesados por ubicacion, modelo, clases detectadas y metadatos.</p>
  </div>

  <div class="card mb-4">
    <div class="card-header header-info">
      <i class="bi bi-funnel me-2"></i>Filtros de busqueda
    </div>
    <div class="card-body">
      <div v-if="error" class="alert alert-danger">
        <i class="bi bi-exclamation-triangle me-2"></i>{{ error }}
      </div>

      <div class="row g-3 mb-3">
        <div class="col-md-3">
          <label class="form-label">Lat min</label>
          <input v-model="latMin" type="number" step="any" class="form-control" />
        </div>
        <div class="col-md-3">
          <label class="form-label">Lat max</label>
          <input v-model="latMax" type="number" step="any" class="form-control" />
        </div>
        <div class="col-md-3">
          <label class="form-label">Lon min</label>
          <input v-model="lonMin" type="number" step="any" class="form-control" />
        </div>
        <div class="col-md-3">
          <label class="form-label">Lon max</label>
          <input v-model="lonMax" type="number" step="any" class="form-control" />
        </div>
      </div>

      <div class="row g-3 mb-3">
        <div class="col-md-4">
          <label class="form-label">Modelo (opcional)</label>
          <input v-model="modelId" type="text" class="form-control" placeholder="yolo11n.pt" />
        </div>
        <div class="col-md-4">
          <label class="form-label">Clases (separadas por coma)</label>
          <input v-model="classes" type="text" class="form-control" placeholder="person, car" />
        </div>
        <div class="col-md-4">
          <label class="form-label">Metadata (JSON)</label>
          <input v-model="metadata" type="text" class="form-control" placeholder='{"camara":"cam_01"}' />
        </div>
      </div>

      <button class="btn btn-primary" @click="handleSearch" :disabled="loading">
        <i class="bi bi-search me-1"></i>
        {{ loading ? 'Buscando...' : 'Buscar' }}
      </button>
    </div>
  </div>

  <div v-if="results !== null">
    <div class="d-flex align-items-center gap-3 mb-3">
      <div class="stat-number text-primary">{{ results.length }}</div>
      <div class="stat-label">Resultado(s) encontrado(s)</div>
    </div>

    <div v-if="results.length === 0" class="alert alert-info">
      <i class="bi bi-info-circle me-2"></i>No se encontraron fotogramas con esos filtros.
    </div>

    <div class="card" v-else>
      <div class="table-responsive">
        <table class="table table-hover mb-0">
          <thead>
            <tr>
              <th>Frame ID</th>
              <th>Metadata</th>
              <th>Detecciones</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in results" :key="r.frameId">
              <td><code>{{ r.frameId.substring(0, 8) }}...</code></td>
              <td>
                <small>
                  <span v-for="(val, key) in r.metadata" :key="key" class="badge bg-light text-dark me-1">
                    {{ key }}: {{ val }}
                  </span>
                </small>
              </td>
              <td>
                <span v-for="(det, i) in r.detections" :key="i">
                  <span v-for="obj in (det.objects || [])" :key="obj.class" class="badge bg-primary me-1">
                    {{ obj.class }} {{ (obj.confidence * 100).toFixed(0) }}%
                  </span>
                </span>
              </td>
              <td>
                <div class="btn-group">
                  <button class="btn btn-sm btn-outline-primary" @click="showPreview(r.frameId)">
                    <i class="bi bi-image me-1"></i>Ver
                  </button>
                  <button
                    class="btn btn-sm btn-outline-secondary"
                    :disabled="downloadingId === `${r.frameId}-false`"
                    @click="downloadImage(r.frameId, false)"
                  >
                    <i class="bi bi-download me-1"></i>Foto
                  </button>
                  <button
                    class="btn btn-sm btn-outline-secondary"
                    :disabled="downloadingId === `${r.frameId}-true`"
                    @click="downloadImage(r.frameId, true)"
                  >
                    <i class="bi bi-download me-1"></i>Thumbnail
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <div v-if="previewUrl" class="modal d-block" tabindex="-1" style="background:rgba(0,0,0,0.6)" @click.self="closePreview">
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title"><i class="bi bi-image me-2"></i>Vista previa</h5>
          <button type="button" class="btn-close" @click="closePreview"></button>
        </div>
        <div class="modal-body text-center p-4">
          <img :src="previewUrl" class="img-fluid rounded" />
        </div>
      </div>
    </div>
  </div>
</template>
