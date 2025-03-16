<template>
  <header>
    <img alt="Vue logo" class="logo" src="./assets/logo.svg" width="125" height="125" />
  </header>

  <main>
    <div class="wrapper">
      <form class="w-full h-full" @submit.prevent="onSubmit">
        <div class="flex flex-col gap-8">
          <input class="bg-white text-black" v-model="username" placeholder="Adresse email" autocomplete="off" test="email" />
          <input class="bg-white text-black" v-model="password" placeholder="Mot de passe" autocomplete="off" type="password"/>
          <button class="bg-white text-black rounded hover:bg-green-300 cursor-pointer" type="submit">Login</button>
        </div>
      </form>
    </div>
  </main>
</template>

<style scoped>
.wrapper {
  width: 300px;
  height: 300px;
}
</style>

<script setup lang="ts">
import {useRouter} from "vue-router";

const router = useRouter();
import {inject, ref} from 'vue'
import AuthProvider from "@/services/authentication.ts";
import {globalState} from "@/services/state.ts";

const authProvider: typeof AuthProvider | undefined = inject('AuthProvider')

const username = ref("")
const password = ref("")

const onSubmit = async () => {
  const result = await authProvider?.authenticate(username.value, password.value);

  if(result?.data.auth) {
    globalState.receiverCode = result.data.user.user_code;
    await router.replace({ path: '/deposit' }).then(console.log).catch(console.log)
  }
}
</script>
