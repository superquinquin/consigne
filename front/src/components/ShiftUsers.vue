<script setup lang="ts">
import { inject, reactive } from 'vue'
import UsersProvider, { type User } from '@/services/users.ts'
import UserCard from '@/components/UserCard.vue'

const usersProvider: typeof UsersProvider | undefined = inject('UsersProvider')

defineProps<{
  selectedUserId?: string
}>()

const state = reactive({
  loading: false,
  shiftUsers: [] as User[],
})

state.loading = true

const result = await usersProvider
  ?.getShiftsUsers()
  .then((data) => data.data.users.map(usersProvider?.parseUser))

if (result) {
  state.shiftUsers = result
}
state.loading = false
</script>

<template v-if="state.shiftUsers.length > 0">
  <div>
    <h2 class="text-2xl text-black font-bold">Coopérateur du créneau</h2>
    <div class="flex w-full flex-wrap">
      <div
        class="p-2"
        v-for="item in state.shiftUsers"
        :key="item.coopNumber"
        @click="$emit('select-user', item)"
      >
        <UserCard :user="item" :is-selected="selectedUserId === item.coopNumber.toString()" />
      </div>
    </div>
  </div>
</template>

<style scoped></style>
