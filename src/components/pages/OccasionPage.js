import get from 'lodash.get'
import React, { Component } from 'react'
import { connect } from 'react-redux'
import { NavLink } from 'react-router-dom'
import { compose } from 'redux'

import OccasionForm from '../OccasionForm'
import withCurrentOccasion from '../hocs/withCurrentOccasion'
import FormField from '../layout/FormField'
import Label from '../layout/Label'
import PageWrapper from '../layout/PageWrapper'
import SubmitButton from '../layout/SubmitButton'
import { resetForm } from '../../reducers/form'
import { closeModal, showModal } from '../../reducers/modal'
import { showNotification } from '../../reducers/notification'
import createEventSelector from '../../selectors/createEvent'
import createTypeSelector from '../../selectors/createType'
import createOffererSelector from '../../selectors/createOfferer'
import createOfferersSelector from '../../selectors/createOfferers'
import createThingSelector from '../../selectors/createThing'
import createVenueSelector from '../../selectors/createVenue'
import createVenuesSelector from '../../selectors/createVenues'
import { eventNormalizer } from '../../utils/normalizers'
import { NEW } from '../../utils/config'

const requiredEventAndThingFields = [
  'name',
  'type',
  'description',
  'contactName',
  'contactEmail',
]

const requiredEventFields = [
  'durationMinutes',
]

class OccasionPage extends Component {
  constructor () {
    super()
    this.state = {
      isReadOnly: true,
      hasNoVenue: false
    }
  }

  static getDerivedStateFromProps (nextProps) {
    const {
      location: { search },
      isNew,
      occasion,
      type,
    } = nextProps
    const {
      id
    } = (occasion || {})
    const isEdit = search === '?modifie'
    const isEventType = get(type, 'model') === 'EventType'
    const isReadOnly = !isNew && !isEdit

    const apiPath = isEventType
      ? `events${id ? `/${id}` : ''}`
      : `things${id ? `/${id}` : ''}`

    let requiredFields = requiredEventAndThingFields

    if (isEventType) {
      requiredFields = requiredFields.concat(requiredEventFields)
    }

    return {
      apiPath,
      isEventType,
      isReadOnly,
      requiredFields
    }
  }

  handleDataRequest = (handleSuccess, handleError) => {
    const {
      history,
      requestData,
      showModal,
      user
    } = this.props

    if (!user) {
      return
    }

    requestData(
      'GET',
      'offerers',
      {
        handleSuccess: (state, action) => {
          if (!get(state, 'data.venues.length')) {
            showModal(
              <div>
                Vous devez avoir déjà enregistré un lieu
                dans une de vos structures pour ajouter des offres
              </div>, {
                onCloseClick: () => history.push('/structures')
              })
          }
          handleSuccess()
        },
        handleError,
        normalizer: { managedVenues: 'venues' }
      }
    )
    requestData('GET', 'types')
  }

  handleSuccessData = (state, action) => {
    const {
      data,
      method
    } = action
    const {
      closeModal,
      history,
      showModal,
      showNotification,
      venue
    } = this.props
    const {
      isEventType
    } = this.state

    showNotification({
      text: 'Votre offre a bien été enregistrée',
      type: 'success'
    })

    // PATCH
    if (method === 'PATCH') {
      history.push('/offres')
      return
    }

    // POST
    if (isEventType && method === 'POST') {
      const { occasions } = (data || {})
      console.log('VENUE', venue)
      const occasion = occasions && occasions.find(o =>
        o.venueId === get(venue, 'id'))
      if (!occasion) {
        console.warn("Something wrong with returned data, we should retrieve the created occasion here")
        return
      }
      showModal(
        <div>
          Cette offre est-elle soumise à des dates ou des horaires particuliers ?
          <NavLink
            className='button'
            to={`/offres/${occasion.id}/dates`}
          >
            Oui
          </NavLink>
          <button onClick={() => { closeModal(); history.push('/offres') }}
            className='button'>
            Non
          </button>
        </div>
      )
    }
  }

  componentWillUnmount () {
    this.props.resetForm()
  }

  render () {
    const {
      event,
      isNew,
      location: { pathname },
      occasionIdOrNew,
      routePath,
      thing,
      type,
      typeOptions,
    } = this.props
    const {
      name
    } = (event || thing || {})
    const {
      apiPath,
      isReadOnly,
      requiredFields
    } = this.state

    const typeOptionsWithPlaceholder = get(typeOptions, 'length') > 1
      ? [{ label: "Sélectionnez un type d'offre" }].concat(typeOptions)
      : typeOptions

    const showAllForm = type || !isNew

    return (
      <PageWrapper
        backTo={{path: '/offres', label: 'Vos offres'}}
        name='offer'
        handleDataRequest={this.handleDataRequest}
      >
        <div className='section'>
          <h1 className='pc-title'>
            {
              isNew
                ? 'Ajouter'
                : 'Modifier'
            } une offre
          </h1>
          <p className='subtitle'>
            Renseignez les détails de cette offre et mettez-la en avant en ajoutant une ou plusieurs accorches.
          </p>
          <FormField
            collectionName='occasions'
            defaultValue={name}
            entityId={occasionIdOrNew}
            isHorizontal
            isExpanded
            label={<Label title="Titre de l'offre :" />}
            name="name"
            readOnly={isReadOnly}
            required={!isReadOnly}
          />
          <FormField
            collectionName='occasions'
            defaultValue={get(type, 'value')}
            entityId={occasionIdOrNew}
            isHorizontal
            label={<Label title="Type :" />}
            name="type"
            options={typeOptionsWithPlaceholder}
            readOnly={isReadOnly}
            required={!isReadOnly}
            type="select"
          />
        </div>

        {
          showAllForm && <OccasionForm {...this.props} {...this.state} />
        }

        <hr />
        <div className="field is-grouped is-grouped-centered" style={{justifyContent: 'space-between'}}>
          <div className="control">
            {
              isReadOnly
                ? (
                  <NavLink to={`${pathname}?modifie`} className='button is-secondary is-medium'>
                    Modifier l'offre
                  </NavLink>
                )
                : (
                  <NavLink
                    className="button is-secondary is-medium"
                    to='/offres'>
                    Annuler
                  </NavLink>
                )
            }
          </div>
          <div className="control">
            {
              isReadOnly
                ? (
                  <NavLink to={routePath} className='button is-primary is-medium'>
                    Terminer
                  </NavLink>
                )
                : (
                  <SubmitButton
                    className="button is-primary is-medium"
                    getBody={form => {
                      const occasionForm = Object.assign({},
                        get(form, `occasionsById.${occasionIdOrNew}`))
                      // remove the EventType. ThingType.
                      if (occasionForm.type) {
                        occasionForm.type = occasionForm.type.split('.')[1]
                      }
                      return occasionForm
                    }}
                    getIsDisabled={form => {
                      if (!requiredFields) {
                        return true
                      }
                      const missingFields = requiredFields.filter(r =>
                        !get(form, `occasionsById.${occasionIdOrNew}.${r}`))
                      return isNew
                        ? missingFields.length > 0
                        : missingFields.length === requiredFields.length
                    }}
                    handleSuccess={this.handleSuccessData}
                    normalizer={eventNormalizer}
                    method={isNew ? 'POST' : 'PATCH'}
                    path={apiPath}
                    storeKey="events"
                    text="Enregistrer"
                  />
                )
              }
          </div>
        </div>
      </PageWrapper>
    )
  }
}

const eventSelector = createEventSelector()
const offerersSelector = createOfferersSelector()
const offererSelector = createOffererSelector(offerersSelector)
const thingSelector = createThingSelector()
const typeSelector = createTypeSelector(eventSelector, thingSelector)
const venuesSelector = createVenuesSelector()
const venueSelector = createVenueSelector(venuesSelector)

export default compose(
  withCurrentOccasion,
  connect(
    (state, ownProps) => {
      const eventId = get(ownProps, 'occasion.eventId')
      const occasionId = get(ownProps, 'occasion.id') || NEW
      const thingId = get(ownProps, 'occasion.thingId')
      const formLabel = get(state, `form.occasionsById.${occasionId}.type`)
      const venueId = get(ownProps, 'occasion.venueId')

      let venue = venueSelector(state, null, venueId)
      const offerers = offerersSelector(state)
      // if there is only one offerer in the list,
      // well choose it
      const offerer = offererSelector(state, get(venue, 'managingOffererId'))
        || (get(offerers, 'length') === 1 && get(offerers, '0'))
      const venues = venuesSelector(state,
        get(state, `form.occasionsById.${occasionId}.offererId`))
      // same for the venue...
      venue = venue || (get(venues, 'length') === 1 && get(venues, '0'))

      return {
        event: eventSelector(state, eventId),
        type: typeSelector(state, eventId || thingId, formLabel),
        thing: thingSelector(state, thingId),
        typeOptions: state.data.types,
        offerer,
        offerers,
        venue,
        venues
      }
    },
    {
      closeModal,
      resetForm,
      showModal,
      showNotification
    }
  )
)(OccasionPage)
