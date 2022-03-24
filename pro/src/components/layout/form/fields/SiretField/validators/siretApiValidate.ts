import { getSiretDataAdapter } from 'core/Venue'

const siretApiValidate = async (siret: string): Promise<string | undefined> => {
  const entrepriseData = await getSiretDataAdapter(siret)
  return entrepriseData.isOk ? undefined : entrepriseData.message
}

export default siretApiValidate
