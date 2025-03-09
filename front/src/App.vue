<script setup lang="ts">

</script>

<template>
  <RouterView/>
</template>

<style>
@import "tailwindcss";

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
