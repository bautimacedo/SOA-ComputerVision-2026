import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref(localStorage.getItem('access_token'))
  const refreshToken = ref(localStorage.getItem('refresh_token'))
  const person = ref(JSON.parse(localStorage.getItem('person') || 'null'))

  const isLoggedIn = computed(() => !!accessToken.value)

  function setSession(tokens, personData) {
    accessToken.value = tokens.access_token
    refreshToken.value = tokens.refresh_token
    person.value = personData
    localStorage.setItem('access_token', tokens.access_token)
    localStorage.setItem('refresh_token', tokens.refresh_token)
    if (personData) localStorage.setItem('person', JSON.stringify(personData))
  }

  function logout() {
    accessToken.value = null
    refreshToken.value = null
    person.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('person')
  }

  async function tryRefresh() {
    try {
      const res = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken.value }),
      })
      if (!res.ok) { logout(); return false }
      const data = await res.json()
      accessToken.value = data.access_token
      refreshToken.value = data.refresh_token
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      return true
    } catch {
      logout()
      return false
    }
  }

  return { accessToken, refreshToken, person, isLoggedIn, setSession, logout, tryRefresh }
})
