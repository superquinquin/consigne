<script setup lang="ts">
import type { User } from '@/services/users'

const { user, isSelected } = defineProps<{
  user: User
  isSelected: boolean
}>()

const { coopNumber, firstName, lastName, fullName, profilePictureUrl } = user

// Création de la photo (ou initiales si pas de photo)
const initials = `${firstName?.charAt(0) || 'N'}${lastName?.charAt(0) || 'D'}`
</script>

<template>
  <div
    :class="`${isSelected ? 'border-2 border-blue-500 bg-blue-50' : 'border-gray-200'}`"
    class="flex flex-col items-center p-4 h-48 w-60 border rounded-lg cursor-pointer transition-all duration-200 bg-white text-center hover:translate-y-[-5px] hover:shadow-md hover:bg-blue-50"
  >
    <img
      v-if="profilePictureUrl"
      :src="profilePictureUrl"
      :alt="firstName"
      class="w-24 h-24 rounded-full object-cover mb-4"
    />
    <div
      v-if="!profilePictureUrl"
      class="w-24 h-24 rounded-full bg-gray-100 flex items-center justify-center text-3xl text-gray-500 mb-4"
    >
      {{ initials }}
    </div>
    <div class="mb-2">
      <div class="font-bold text-lg mb-1 text-gray-600">
        {{ firstName && lastName ? firstName + ' ' + lastName : fullName }}
      </div>
      <div class="text-gray-500 text-sm">{{ coopNumber }}</div>
    </div>
  </div>
</template>
