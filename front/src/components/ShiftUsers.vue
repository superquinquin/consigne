<script setup lang="ts">
import { inject, reactive } from 'vue'
import UsersProvider, { type GetShiftsUsersResponse } from '@/services/users.ts'
import UserCard from '@/components/UserCard.vue'

const usersProvider: typeof UsersProvider | undefined = inject('UsersProvider')

defineProps<{
  selectedUserId?: string
}>()

const state = reactive({
  loading: false,
  shiftUsers: [] as GetShiftsUsersResponse['users'],
})

state.loading = true

const result = await usersProvider?.getShiftsUsers().then((data) =>
  data.data.users.map((item: [number, string]) => ({
    coopNumber: item[0],
    firstName: item[1].split('-')[1].trim().split(',')[1],
    lastName: item[1].split('-')[1].trim().split(',')[0],
    profilePictureUrl: undefined,
  })),
)

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
        @click="$emit('select-user', item.coopNumber)"
      >
        <UserCard
          :profile-picture-url="item.profilePictureUrl"
          :first-name="item.firstName"
          :last-name="item.lastName"
          :coop-number="item.coopNumber"
          :is-selected="selectedUserId === item.coopNumber.toString()"
        />
      </div>
    </div>
  </div>
</template>

<style scoped></style>
