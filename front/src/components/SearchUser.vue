<script setup lang="ts">
import { inject, reactive, ref } from 'vue'
import UserCard from '@/components/UserCard.vue'
import UsersProvider, { type User } from '@/services/users'

defineProps<{
  searchLabel?: string
  selectedUserId?: string
}>()

const userProvider: typeof UsersProvider | undefined = inject('UsersProvider')
const state = reactive({
  loading: false,
  searchResult: undefined as User[] | undefined,
  searchedTerm: '',
  failed: false,
})

const search = ref('')
const onSubmit = async () => {
  if (!search.value || state.loading) {
    return
  }

  state.loading = true
  state.failed = false
  state.searchedTerm = search.value

  try {
    const response = await userProvider?.searchUser(search.value)
    const matches = response?.data?.matches

    // `matches` absent = réponse d'erreur (elle porte quand même du JSON, donc
    // fetch ne lève pas) ; `matches` vide = recherche aboutie sans correspondance.
    if (!matches) {
      throw new Error(response?.reasons ?? 'réponse inattendue')
    }
    state.searchResult = matches.map(userProvider!.parseUser)
  } catch {
    state.failed = true
    state.searchResult = undefined
  } finally {
    state.loading = false
  }
}
</script>

<template>
  <div class="flex flex-col gap-8">
    <div class="flex flex-col gap-2">
      <label class="text-2xl text-black font-bold">{{
        searchLabel ? searchLabel : 'Rechercher un utilisateur'
      }}</label>
      <div class="relative">
        <div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
          <svg
            class="w-4 h-4 text-gray-500"
            aria-hidden="true"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 20 20"
          >
            <path
              stroke="currentColor"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="m19 19-4-4m0-7A7 7 0 1 1 1 8a7 7 0 0 1 14 0Z"
            />
          </svg>
        </div>
        <input
          v-model="search"
          v-on:keyup.enter="onSubmit"
          class="block w-full p-3 pl-10 text-sm text-gray-900 border border-gray-300 rounded-lg bg-white focus:ring-blue-500 focus:border-blue-500 outline-none transition duration-150 ease-in-out"
          placeholder="Rechercher par nom ou numéro..."
          autocomplete="off"
        />
        <button
          @click="onSubmit"
          class="absolute inset-y-0 right-0 flex items-center px-4 text-white bg-blue-500 border border-blue-500 rounded-r-lg hover:bg-blue-600 focus:outline-none"
          :class="{ 'opacity-75 cursor-wait': state.loading }"
          :disabled="state.loading"
        >
          <span v-if="!state.loading">Rechercher</span>
          <svg
            v-else
            class="animate-spin h-5 w-5"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              class="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              stroke-width="4"
            ></circle>
            <path
              class="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            ></path>
          </svg>
        </button>
      </div>
    </div>
    <p
      v-if="!state.loading && state.failed"
      role="alert"
      class="p-4 text-base text-red-800 bg-red-50 border border-red-200 rounded-lg"
    >
      La recherche a échoué. Veuillez réessayer.
    </p>
    <p
      v-else-if="!state.loading && state.searchResult?.length === 0"
      role="status"
      class="p-4 text-base text-amber-900 bg-amber-50 border border-amber-200 rounded-lg"
    >
      Aucun coopérateur ne correspond à «&nbsp;{{ state.searchedTerm }}&nbsp;». Vérifiez
      l'orthographe ou essayez avec le numéro de coopérateur.
    </p>
    <div v-else class="flex flex-row gap-4 overflow-auto">
      <div
        class="p-2"
        v-for="item in state.searchResult"
        :key="item.partnerId"
        @click="$emit('select-user', item)"
        @dblclick="$emit('confirm-user',item)"
      >
        <UserCard :user="item" :is-selected="selectedUserId === item.partnerId.toString()" />
      </div>
    </div>
  </div>
</template>

<style scoped></style>
