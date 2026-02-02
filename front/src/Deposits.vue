<script setup lang="ts">
import {inject, reactive, watch} from 'vue'
import type Deposit from '@/services/deposit.ts'
import SearchUser from '@/components/SearchUser.vue'
import type {User} from './services/users'
import {getGlobalState, setGlobalState} from "@/services/state.ts";
import {useRouter} from "vue-router";
import {useConfirmDialog} from '@vueuse/core';


const globalState = getGlobalState()
const depositProvider: typeof Deposit | undefined = inject('DepositProvider')
const router = useRouter()
const {isRevealed, reveal, confirm, cancel, onConfirm}
  = useConfirmDialog()

onConfirm(async () => {
  await onPrint()
  await onEnd()
})

watch(() => globalState.receiver, async (receiver) => {
  if (!receiver) {
    await router.push({path: '/'})
  }
})

type Returnable = {
  name: string
  isReturnable: boolean
  value: number
}

type DisplayedReturnable = {
  id: number
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
  closeDepositLoading: boolean
}>({
  returnGoods: [],
  barcode: '',
  addProductLoading: false,
  printTicketLoading: false,
  closeDepositLoading: false,
})

const errorState = reactive<{ productName?: string; reasons?: string }>({
  productName: undefined,
  reasons: undefined,
})

const resetError = () => {
  errorState.productName = undefined
  errorState.reasons = undefined
}

const currentTotalValue = () =>
  depositState.returnGoods.reduce((acc, current) => acc + current.value, 0)

const queryForReturnable = async (barCode: string): Promise<Returnable | null> => {
  if (globalState.depositId) {
    const result = await depositProvider?.addProduct(globalState.depositId, barCode)

    if (result?.data) {
      resetError()

      return {
        name: result.data.name,
        isReturnable: result.data.returnable,
        value: result.data.return_value || 0,
      }
    }

    errorState.reasons = result?.reasons

    return null
  }

  return null
}

const groupByBarcode = () =>
  depositState.returnGoods.reduce<Record<string, DisplayedReturnable>>((acc, current, index) => {
    acc[current.name] = {
      id: acc[current.name]?.id || index,
      name: current.name,
      value: current.value + (acc[current.name]?.value || 0),
      quantity: (acc[current.name]?.quantity || 0) + 1,
    }
    return acc
  }, {})

const onSubmit = async (event?: KeyboardEvent) => {
  if (!event || event.code === 'Enter') {
    depositState.addProductLoading = true
    const returnable = await queryForReturnable(depositState.barcode)

    if (returnable?.isReturnable) {
      depositState.returnGoods = [...depositState.returnGoods, returnable]
    } else {
      errorState.productName = returnable?.name
    }

    depositState.barcode = ''
    depositState.addProductLoading = false
  }
}

const selectUser = (user: User) => {
  globalState.provider = user
  setGlobalState(globalState)
}

const onPrint = async () => {
  if (globalState.depositId) {
    depositState.printTicketLoading = true
    void (await depositProvider?.printTicket(globalState.depositId).finally(() => {
      depositState.printTicketLoading = false
    }))
  }
}

const onEnd = async () => {
  if (globalState.depositId) {

    depositState.closeDepositLoading = true
    await depositProvider
      ?.close(globalState.depositId)
      .then(({status, reasons}) => {
        if (status !== 200) {
          errorState.reasons = reasons
        } else {
          globalState.depositId = undefined
          globalState.provider = undefined
          setGlobalState(globalState)
          depositState.returnGoods = []
        }
      })
      .finally(() => (depositState.closeDepositLoading = false))
  }
}

const createDeposit = async () => {
  if (globalState.provider && globalState.receiver) {
    const result = await depositProvider?.create(
      globalState.provider.partnerId,
      globalState.receiver.partnerId,
    )

    if (result?.deposit_id) {
      globalState.depositId = result.deposit_id
      setGlobalState(globalState)
    }
  }
}
</script>

<template>
  <div class="hidden py-4 text-black">Global state : {{ JSON.stringify(globalState) }}</div>
  <div class="hidden py-4 text-black">Deposit state : {{ JSON.stringify(depositState) }}</div>
  <main class="w-full h-full">
    <template v-if="!globalState.depositId">
      <div class="flex flex-col gap-2 px-auto">
        <SearchUser
          @select-user="selectUser"
          @confirm-user="createDeposit"
          search-label="Identifier le membre qui rapporte des bouteilles"
          :selected-user-id="globalState.provider?.partnerId.toString()"
        />
        <button @click="createDeposit" type="button">Démarrer le dépôt</button>
      </div>
    </template>

    <template v-else>
      <div class="flex flex-col gap-16">
        <div class="wrapper">
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
              v-model="depositState.barcode"
              v-on:keyup.enter="onSubmit"
              :disabled="depositState.addProductLoading"
              class="block w-full p-3 pl-10 text-sm text-gray-900 border border-gray-300 rounded-lg bg-white focus:ring-blue-500 focus:border-blue-500 outline-none transition duration-150 ease-in-out"
              placeholder="Scannez un produit"
              autocomplete="off"
            />
            <button
              @click="() => onSubmit()"
              class="absolute inset-y-0 right-0 flex items-center px-4 text-white bg-blue-500 border border-blue-500 rounded-r-lg hover:bg-blue-600 focus:outline-none"
              :class="{ 'opacity-75 cursor-wait': depositState.addProductLoading }"
              :disabled="depositState.addProductLoading"
            >
              <span v-if="!depositState.addProductLoading">Ajouter</span>
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

        <div v-if="errorState.productName" class="text-xl text-red-500">
          {{ errorState.productName }} n'est pas consigné !
        </div>

        <div v-if="errorState.reasons" class="text-xl text-red-500">
          Une erreur semble avoir apparut :
          {{ errorState.reasons }}
        </div>

        <div class="flex flex-col gap-4" v-if="depositState.returnGoods.length !== 0">
          <div
            class="text-black text-xl border-1 border-gray-300 rounded bg-white p-2 flex flex-col gap-2"
          >
            <div v-for="value in groupByBarcode()" :key="value.id">
              ⋅ {{ value.quantity }} x {{ value.name }} - {{ value.value.toFixed(2) }} €
            </div>
          </div>
          <div class="text-black text-2xl">Total : {{ currentTotalValue().toFixed(2) }} €</div>
        </div>

        <div v-else>
          <span class="text-black text-2xl">
            Aucun produit consigné n'a été scanné pour le moment</span
          >
        </div>

        <div class="flex flex-row gap-8">
          <button @click="reveal" type="button">
            <span v-if="!depositState.printTicketLoading">Imprimer le reçu</span>
            <svg
              v-else
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
          <button @click="onEnd" type="button">
            <span v-if="!depositState.closeDepositLoading">Annuler et retourner à l'accueil</span>
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

      <teleport to="body">
        <div v-if="isRevealed" class="modal-bg">
          <div class="modal rounded-xl">
            <h2 class="text-xl text-black p-10">Êtes vous sûr de vouloir imprimer le reçu et clôturer le
              dépôt ?</h2>
            <div class="flex flex-row gap-4 justify-center">
              <button class="bg-black" @click="confirm" type="button">
                Oui
              </button>
              <button class="bg-red" @click="cancel" type="button">
                Continuer a modifier le dépôt
              </button>
            </div>
          </div>
        </div>
      </teleport>
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

.modal-bg {
  position: fixed;
  top: 0;
  left: 0;
  height: 100%;
  width: 100%;
  background-color: rgba(0, 0, 0, .5);
  display: flex;
  justify-content: center;
  align-items: center;
}

.modal {
  position: relative;
  background-color: white;
  padding: 2em 1em;
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
