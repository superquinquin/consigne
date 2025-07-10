<script setup lang="ts">
import {getGlobalState, setGlobalState} from "@/services/state.ts";

const globalState = getGlobalState();

const resetCoop = () => {
  setGlobalState({
    receiver: undefined,
    provider: undefined,
  })
};
</script>

<template>
  <header class="flex flex-row justify-between items-center">
    <div class="flex flex-col">
      <h1 class="text-black text-4xl">Retournez vos bouteilles ! 🔄</h1>
      <span v-if="!!globalState.receiver" class="text-black text-xl"
        >Coopérateur en charge :
        {{
          globalState.receiver?.firstName && globalState.receiver?.lastName
            ? globalState.receiver?.firstName + ' ' + globalState.receiver?.lastName
            : globalState.receiver?.fullName
        }}
      </span>
      <span v-if="!!globalState.provider" class="text-black text-xl"
        >Coopérateur ramenant ses consignes :
        {{
          globalState.provider?.firstName && globalState.provider?.lastName
            ? globalState.provider?.firstName + ' ' + globalState.provider?.lastName
            : globalState.provider?.fullName
        }}
      </span>
      <button v-if="!!globalState.receiver || !!globalState.provider" class="" type="button" @click="resetCoop()">Changer les coopérateurs</button>
    </div>
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
