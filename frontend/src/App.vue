<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from './stores/auth.js'
import Navbar from './components/Navbar.vue'

const auth = useAuthStore()
const route = useRoute()

const isAuthPage = computed(() => route.name === 'Login' || route.name === 'Register')
</script>

<template>
  <template v-if="isAuthPage">
    <router-view />
  </template>
  <template v-else>
    <Navbar v-if="auth.isLoggedIn" />
    <div class="container main-content">
      <router-view />
    </div>
  </template>
</template>
