<script setup lang="ts">
import { inject, reactive, ref } from 'vue'
import AuthProvider, { type SearchUserResponse } from '@/services/authentication.ts'
import UserCard from '@/components/UserCard.vue'

// defineProps<{}>()

const authProvider: typeof AuthProvider | undefined = inject('AuthProvider')
const state = reactive({
  loading: false,
  searchResult: undefined as SearchUserResponse | undefined,
  selectUserId: undefined,
})

const search = ref('')
const onSubmit = async () => {
  state.loading = true

  if (search.value) {
    const result = await authProvider?.searchUser(search.value).then((data) =>
      data.data.matches?.map((item: [number, string]) => ({
        coopNumber: item[0],
        firstName: item[1].split('-')[1].trim().split(',')[1],
        lastName: item[1].split('-')[1].trim().split(',')[0],
        profilePictureUrl: undefined,
      })),
    )
    if (result) {
      state.searchResult = result
    }
    state.loading = false
  }
}
</script>

<template>
  <div class="flex flex-col gap-8">
    <div class="flex flex-col w-1/3 gap-2">
      <label class="text-2xl text-black font-bold">Rechercher un utilisateur</label>
      <input
        v-model="search"
        v-on:keyup.enter="onSubmit"
        class="bg-white text-black"
        placeholder="Nicolas"
        autocomplete="off"
      />
    </div>
    <div class="flex flex-row gap-4 overflow-auto">
      <div
        v-for="item in state.searchResult"
        :key="item.coopNumber"
        @click="
          () => {
            state.selectUserId = item.coopNumber
            $emit('select-user', item.coopNumber)
          }
        "
      >
        <UserCard
          :profile-picture-url="item.profilePictureUrl"
          :first-name="item.firstName"
          :last-name="item.lastName"
          :coop-number="item.coopNumber"
          :is-selected="state.selectUserId === item.coopNumber"
        />
      </div>
    </div>
  </div>
</template>

<style scoped></style>
