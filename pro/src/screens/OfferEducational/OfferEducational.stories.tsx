import React from 'react'

import { INITIAL_EDUCATIONAL_FORM_VALUES } from 'core/OfferEducational'

import { withPageTemplate } from '../../stories/decorators/withPageTemplate'
import { withRouterDecorator } from '../../stories/decorators/withRouter'

import { categoriesFactory } from './__tests-utils__/categoryFactory'
import { subCategoriesFactory } from './__tests-utils__/subCategoryFactory'
import OfferEducational from './OfferEducational'

const mockEducationalCategories = categoriesFactory([
  {
    id: 'MUSEE',
    proLabel: 'Musée, patrimoine, architecture, arts visuels',
  },
  {
    id: 'CINEMA',
    proLabel: 'Cinéma',
  },
])

const mockEducationalSubcategories = subCategoriesFactory([
  {
    id: 'CINE_PLEIN_AIR',
    categoryId: 'CINEMA',
    proLabel: 'Cinéma plein air',
  },
  {
    id: 'EVENEMENT_CINE',
    categoryId: 'CINEMA',
    proLabel: 'Événement cinématographique',
  },
  {
    id: 'VISITE_GUIDEE',
    categoryId: 'MUSEE',
    proLabel: 'Visite guidée',
  },
])

export default {
  title: 'scrrens/OfferEducational',
  component: OfferEducational,
  decorators: [withRouterDecorator, withPageTemplate],
}

const Template = () => (
  <OfferEducational
    educationalCategories={mockEducationalCategories}
    educationalSubcategories={mockEducationalSubcategories}
    initialValues={INITIAL_EDUCATIONAL_FORM_VALUES}
    onSubmit={() => null}
  />
)

export const Default = Template.bind({})
