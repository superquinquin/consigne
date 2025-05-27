<script setup lang="ts">
import { inject, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import type Deposit from '@/services/deposit.ts'
import SearchUser from '@/components/SearchUser.vue'
import { globalState } from '@/services/state.ts'
import deposit from '@/services/deposit.ts'

const router = useRouter()
const depositProvider: typeof Deposit = inject('DepositProvider')

type Returnable = {
  name: string
  isReturnable: boolean
  value: number
}

type DisplayedReturnable = {
  name: string
  value: number
  quantity: number
}

const depositState = reactive<{
  returnGoods: Returnable[]
  barcode: string
  depositId?: number
  addProductLoading: boolean
  printTicketLoading: boolean
}>({
  returnGoods: [],
  barcode: '',
  addProductLoading: false,
  printTicketLoading: false,
})

const errorState = reactive<{ productName?: string }>({ productName: undefined })

const currentTotalValue = () =>
  depositState.returnGoods.reduce((acc, current) => acc + current.value, 0)

const queryForReturnable = async (barCode: string): Promise<Returnable | null> => {
  const result = await depositProvider.addProduct(globalState.depositId, barCode)

  return {
    name: result.name,
    isReturnable: result.returnable,
    value: result.return_value || 0,
  }
}

const groupByBarcode = () =>
  depositState.returnGoods.reduce<Record<string, DisplayedReturnable>>((acc, current) => {
    acc[current.name] = {
      name: current.name,
      value: current.value + (acc[current.name]?.value || 0),
      quantity: (acc[current.name]?.quantity || 0) + 1,
    }
    return acc
  }, {})

const onSubmit = async (event: KeyboardEvent) => {
  if (event.code === 'Enter') {
    depositState.addProductLoading = true
    const returnable = await queryForReturnable(depositState.barcode)

    console.log(returnable)

    if (returnable?.isReturnable) {
      errorState.productName = undefined
      depositState.returnGoods = [...depositState.returnGoods, returnable]
    } else {
      errorState.productName = returnable?.name
    }

    depositState.barcode = ''
    depositState.addProductLoading = false
  }
}

const selectUser = (userId: number) => {
  console.log(`Selected User : ${userId}`)
  globalState.providerCode = userId.toString()
}

const onPrint = async () => {
  depositState.printTicketLoading = true
  void (await depositProvider.printTicket(globalState.depositId).finally(() => {
    depositState.printTicketLoading = false
  }))
}

const onEnd = async () => {
  await depositProvider.close(globalState.depositId).finally(() => {
    globalState.depositId = undefined
    globalState.providerCode = ''
    depositState.returnGoods = []
  })
}

const createDeposit = async () => {
  const result = await depositProvider.create(globalState.providerCode, globalState.receiverCode)

  if (result.deposit_id) {
    globalState.depositId = result.deposit_id
  }
}
</script>

<template>
  <div class="hidden py-4 text-black">Global state : {{ JSON.stringify(globalState) }}</div>
  <div class="hidden py-4 text-black">Deposit state : {{ JSON.stringify(depositState) }}</div>
  <main class="w-full h-full">
    <div class="text-black">
      Afin de tester, essayez les codes barres suivant : 3770000661170, 5411087001562,
      3361730666667, 3770000661071
    </div>
    <br />
    <template v-if="!globalState.depositId">
      <div class="flex flex-col gap-2 px-auto">
        <SearchUser
          @select-user="selectUser"
          search-label="Sélectionner le coopérateur donnant ses consignes"
          :selected-user-id="globalState.providerCode"
        />
        <button @click="createDeposit" type="button">Démarrer le dépôt</button>
      </div>
    </template>

    <template v-else>
      <div class="flex flex-col gap-16">
        <div class="wrapper">
          <input
            v-model="depositState.barcode"
            v-on:keydown="onSubmit"
            placeholder="Scannez un produit"
            autocomplete="off"
          />
          <svg
            v-if="depositState.addProductLoading"
            aria-hidden="true"
            role="status"
            class="inline w-4 h-4 ms-6 text-black animate-spin"
            viewBox="0 0 100 101"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M100 50.5908C100 78.2051 77.6142 100.591 50 100.591C22.3858 100.591 0 78.2051 0 50.5908C0 22.9766 22.3858 0.59082 50 0.59082C77.6142 0.59082 100 22.9766 100 50.5908ZM9.08144 50.5908C9.08144 73.1895 27.4013 91.5094 50 91.5094C72.5987 91.5094 90.9186 73.1895 90.9186 50.5908C90.9186 27.9921 72.5987 9.67226 50 9.67226C27.4013 9.67226 9.08144 27.9921 9.08144 50.5908Z"
              fill="#E5E7EB"
            />
            <path
              d="M93.9676 39.0409C96.393 38.4038 97.8624 35.9116 97.0079 33.5539C95.2932 28.8227 92.871 24.3692 89.8167 20.348C85.8452 15.1192 80.8826 10.7238 75.2124 7.41289C69.5422 4.10194 63.2754 1.94025 56.7698 1.05124C51.7666 0.367541 46.6976 0.446843 41.7345 1.27873C39.2613 1.69328 37.813 4.19778 38.4501 6.62326C39.0873 9.04874 41.5694 10.4717 44.0505 10.1071C47.8511 9.54855 51.7191 9.52689 55.5402 10.0491C60.8642 10.7766 65.9928 12.5457 70.6331 15.2552C75.2735 17.9648 79.3347 21.5619 82.5849 25.841C84.9175 28.9121 86.7997 32.2913 88.1811 35.8758C89.083 38.2158 91.5421 39.6781 93.9676 39.0409Z"
              fill="currentColor"
            />
          </svg>
        </div>

        <div class="text-black">
          <ul>
            <li v-for="value in groupByBarcode()">
              {{ value.name }} - x{{ value.quantity }} {{ value.value.toFixed(2) }} euros
            </li>
          </ul>
          Total : {{ currentTotalValue().toFixed(2) }} euros
        </div>

        <div v-if="errorState.productName" class="text-red-500">
          {{ errorState.productName }} n'est pas consigné !
        </div>

        <div class="flex flex-row gap-8">
          <button @click="onPrint" type="button">
            Print
            <svg
              v-if="depositState.printTicketLoading"
              aria-hidden="true"
              role="status"
              class="inline w-4 h-4 me-3 text-black animate-spin"
              viewBox="0 0 100 101"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <path
                d="M100 50.5908C100 78.2051 77.6142 100.591 50 100.591C22.3858 100.591 0 78.2051 0 50.5908C0 22.9766 22.3858 0.59082 50 0.59082C77.6142 0.59082 100 22.9766 100 50.5908ZM9.08144 50.5908C9.08144 73.1895 27.4013 91.5094 50 91.5094C72.5987 91.5094 90.9186 73.1895 90.9186 50.5908C90.9186 27.9921 72.5987 9.67226 50 9.67226C27.4013 9.67226 9.08144 27.9921 9.08144 50.5908Z"
                fill="#E5E7EB"
              />
              <path
                d="M93.9676 39.0409C96.393 38.4038 97.8624 35.9116 97.0079 33.5539C95.2932 28.8227 92.871 24.3692 89.8167 20.348C85.8452 15.1192 80.8826 10.7238 75.2124 7.41289C69.5422 4.10194 63.2754 1.94025 56.7698 1.05124C51.7666 0.367541 46.6976 0.446843 41.7345 1.27873C39.2613 1.69328 37.813 4.19778 38.4501 6.62326C39.0873 9.04874 41.5694 10.4717 44.0505 10.1071C47.8511 9.54855 51.7191 9.52689 55.5402 10.0491C60.8642 10.7766 65.9928 12.5457 70.6331 15.2552C75.2735 17.9648 79.3347 21.5619 82.5849 25.841C84.9175 28.9121 86.7997 32.2913 88.1811 35.8758C89.083 38.2158 91.5421 39.6781 93.9676 39.0409Z"
                fill="currentColor"
              />
            </svg>
          </button>
          <button @click="onEnd" type="button">End deposit</button>
        </div>
      </div>
    </template>
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
