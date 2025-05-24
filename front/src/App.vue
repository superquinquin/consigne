<script setup lang="ts"></script>

<template>
  <header class="flex flex-row justify-between items-center">
    <h1 class="text-black text-4xl">Retournez vos bouteilles ! 🔄</h1>
    <img
      alt="Vue logo"
      class="logo"
      src="./assets/bouteille%20de%20biere.webp"
      width="300"
      height="300"
    />
  </header>
  <RouterView />
</template>

<style>
@import 'tailwindcss';

body {
  background: #f1f2e9;
}

input {
  background-color: white;
  color: black;
}

button {
  background-color: white;
  color: black;
  padding: 0.25em 1em 0.25em;
  border-radius: 0.25rem;
}

button:hover {
  background-color: var(--color-green-300);
}
</style>
