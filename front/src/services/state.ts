import { reactive } from 'vue'

export const globalState = reactive<{providerCode: string; receiverCode:string; depositId?: number}>({
  providerCode: "",
  receiverCode: "",
})
