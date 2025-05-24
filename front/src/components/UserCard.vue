<script setup lang="ts">

const {firstName, lastName, profilePictureUrl, coopNumber, isSelected} = defineProps<{
  profilePictureUrl?: string,
  firstName: string,
  lastName: string,
  coopNumber: number,
  isSelected: boolean,
}>()

// Création de la photo (ou initiales si pas de photo)
const initials = firstName.charAt(0) + lastName.charAt(0);

</script>

<template>
  <div :class="`flex flex-col items-center p-4 border rounded-lg cursor-pointer transition-all duration-200 bg-white text-center ${isSelected ? 'border-2 border-blue-500 bg-blue-50' : 'border-gray-200'}`"
       class="hover:translate-y-[-5px] hover:shadow-md hover:bg-blue-50">
    <img v-if="profilePictureUrl" 
         :src="profilePictureUrl" 
         :alt="firstName" 
         class="w-24 h-24 rounded-full object-cover mb-4">
    <div v-if="!profilePictureUrl" 
         class="w-24 h-24 rounded-full bg-gray-100 flex items-center justify-center text-3xl text-gray-500 mb-4">
      {{initials}}
    </div>
    <div class="mb-2">
      <div class="font-bold text-lg mb-1 text-gray-600">{{firstName}} {{lastName}}</div>
      <div class="text-gray-500 text-sm">{{coopNumber}}</div>
    </div>
  </div>
</template>