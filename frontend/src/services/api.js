const BASE = '/api'

async function request(method, path, { body, formData, headers = {} } = {}) {
  const authStore = (await import('../stores/auth.js')).useAuthStore()

  if (authStore.accessToken) {
    headers['Authorization'] = `Bearer ${authStore.accessToken}`
  }

  const options = { method, headers }

  if (formData) {
    options.body = formData
  } else if (body) {
    headers['Content-Type'] = 'application/json'
    options.body = JSON.stringify(body)
  }

  const res = await fetch(`${BASE}${path}`, options)

  if (res.status === 401 && authStore.refreshToken) {
    const refreshed = await authStore.tryRefresh()
    if (refreshed) {
      headers['Authorization'] = `Bearer ${authStore.accessToken}`
      const retry = await fetch(`${BASE}${path}`, { method, headers, body: options.body })
      return handleResponse(retry)
    }
  }

  return handleResponse(res)
}

async function handleResponse(res) {
  if (res.headers.get('content-type')?.includes('image/')) {
    return { ok: res.ok, status: res.status, blob: await res.blob() }
  }
  const data = res.ok ? await res.json() : null
  const error = !res.ok ? await res.json().catch(() => ({ detail: 'Error desconocido' })) : null
  return { ok: res.ok, status: res.status, data, error }
}

export default {
  get: (path) => request('GET', path),
  post: (path, body) => request('POST', path, { body }),
  postForm: (path, formData) => request('POST', path, { formData }),
}
