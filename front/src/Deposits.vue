<script setup lang="ts">
import {reactive} from "vue";
import {useRouter} from "vue-router";

const router = useRouter()

type Returnable = {
  name: string;
  isReturnable: boolean;
  value: number;
}

type DisplayedReturnable = {
  name: string;
  value: number;
  quantity: number;
}

const mockupReturnable = ["1", "2", "3"];

const state = reactive<{ returnGoods: Returnable[], barcode: string }>({
  returnGoods: [],
  barcode: ""
})

const currentTotalValue = () => state.returnGoods.reduce((acc, current) => acc + current.value, 0)

const queryForReturnable = async (barCode: string): Promise<Returnable | null> => {
  if (mockupReturnable.some(returnable => returnable === barCode)) {
    return {
      name: barCode,
      isReturnable: true,
      value: Math.random() > 0.5 ? 1 : 2
    }
  }

  return null;
}

const groupByBarcode = () =>
    state.returnGoods.reduce<Record<string, DisplayedReturnable>>((acc, current) => {
      acc[current.name] = {name: current.name, value: current.value + (acc[current.name]?.value || 0), quantity: (acc[current.name]?.quantity || 0)+1};
      return acc;
    }, {})

const onSubmit = async (event: KeyboardEvent) => {
  if (event.code === 'Enter') {
    const returnable = await queryForReturnable(state.barcode);

    if (returnable?.isReturnable) {
      state.returnGoods = [...state.returnGoods, returnable]
    }

    state.barcode = "";
  }
}

const onPrint = async () => {

}

const onEnd = async () => {
  await router.push({ path: "/" });
}
</script>

<template>
  <header>
    <img alt="Vue logo" class="logo" src="./assets/logo.svg" width="125" height="125"/>
  </header>

  <main class="w-100 h-100">
    <div class="flex flex-col gap-16">

      <div class="wrapper">
        <input v-model="state.barcode" v-on:keydown="onSubmit" placeholder="Scannez un produit"
               autocomplete="off"/>
      </div>

      <div>
        <ul>
          <li v-for="value in groupByBarcode()">
            {{ value.name }} - x{{value.quantity}} {{ value.value/10 }} euros
          </li>
        </ul>
        Total : {{currentTotalValue()/10}}

      </div>


      <div class="flex flex-row gap-8">
        <button @click="onPrint" type="button">Print</button>
        <button @click="onEnd" type="button">End deposit</button>
      </div>
    </div>
  </main>
</template>

<style scoped>
header {
  line-height: 1.5;
}

.logo {
  display: block;
  margin: 0 auto 2rem;
}

@media (min-width: 1024px) {
  header {
    display: flex;
    place-items: center;
    padding-right: calc(var(--section-gap) / 2);
  }

  .logo {
    margin: 0 2rem 0 0;
  }

  header .wrapper {
    display: flex;
    place-items: flex-start;
    flex-wrap: wrap;
  }
}
</style>
