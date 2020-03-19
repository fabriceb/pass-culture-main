import { mapDispatchToProps, mapStateToProps } from '../DiscoveryContainer'
import { recommendationNormalizer } from '../../../../utils/normalizers'

jest.mock('redux-thunk-data', () => {
  const { assignData, createDataReducer, deleteData, requestData } = jest.requireActual(
    'fetch-normalize-data'
  )
  return {
    assignData,
    createDataReducer,
    deleteData,
    requestData,
  }
})
jest.useFakeTimers()

describe('src | components | pages | discovery | DiscoveryContainer', () => {
  let dispatch
  let replace
  let props

  beforeEach(() => {
    dispatch = jest.fn()
    replace = jest.fn()
    props = {
      history: {
        replace,
      },
      location: {
        search: '',
      },
      match: {
        params: {},
      },
      query: {
        parse: () => ({}),
      },
    }
  })

  describe('mapStateToProps()', () => {
    it('should return an object of props', () => {
      // given
      const state = {
        data: {
          recommendations: [],
        },
        pagination: {
          seedLastRequestTimestamp: 11111111112,
        },
        geolocation: {
          longitude: 48.256756,
          latitude: 2.8796567,
          watchId: 1,
        },
      }

      const ownProps = {
        match: {
          params: {},
        },
      }

      // when
      const props = mapStateToProps(state, ownProps)

      // then
      expect(props).toStrictEqual({
        coordinates: {
          latitude: 2.8796567,
          longitude: 48.256756,
          watchId: 1,
        },
        currentRecommendation: {
          index: 0,
          mediation: {
            frontText:
              'Vous avez parcouru toutes les offres. Revenez bientôt pour découvrir les nouveautés.',
            id: 'fin',
            thumbCount: 1,
            tutoIndex: -1,
          },
          mediationId: 'fin',
          productOrTutoIdentifier: 'tuto_-1',
          thumbUrl: 'http://localhost/splash-finReco@2x.png',
        },
        readRecommendations: undefined,
        recommendations: [],
        seedLastRequestTimestamp: 11111111112,
        shouldReloadRecommendations: true,
        tutorials: [],
      })
    })
  })

  describe('mapDispatchToProps()', () => {
    describe('when mapping loadRecommendations', () => {
      it('should load the recommendations with page equals 1 when no current recommendation', () => {
        // given
        const handleRequestSuccess = jest.fn()
        const handleRequestFail = jest.fn()
        const currentRecommendation = {}
        const recommendations = []
        const readRecommendations = null
        const shouldReloadRecommendations = false
        const functions = mapDispatchToProps(dispatch, props)
        const { loadRecommendations } = functions

        // when
        loadRecommendations(
          handleRequestSuccess,
          handleRequestFail,
          currentRecommendation,
          recommendations,
          readRecommendations,
          shouldReloadRecommendations
        )

        // then
        expect(dispatch.mock.calls[0][0]).toStrictEqual({
          config: {
            apiPath: `/recommendations/v3?`,
            body: {
              readRecommendations: null,
              seenRecommendationIds: [],
            },
            handleFail: handleRequestFail,
            handleSuccess: handleRequestSuccess,
            method: 'PUT',
            normalizer: recommendationNormalizer,
          },
          type: 'REQUEST_DATA_PUT_/RECOMMENDATIONS/V3?',
        })
      })

      it('should load the recommendations with page equals 1 when current recommendation is a tuto', () => {
        // given
        const handleRequestSuccess = jest.fn()
        const handleRequestFail = jest.fn()
        const currentRecommendation = { mediationId: 'tuto' }
        const recommendations = []
        const readRecommendations = null
        const shouldReloadRecommendations = false
        const functions = mapDispatchToProps(dispatch, props)
        const { loadRecommendations } = functions

        // when
        loadRecommendations(
          handleRequestSuccess,
          handleRequestFail,
          currentRecommendation,
          recommendations,
          readRecommendations,
          shouldReloadRecommendations
        )

        // then
        expect(dispatch.mock.calls[0][0]).toStrictEqual({
          config: {
            apiPath: `/recommendations/v3?`,
            body: {
              readRecommendations: null,
              seenRecommendationIds: [],
            },
            handleFail: handleRequestFail,
            handleSuccess: handleRequestSuccess,
            method: 'PUT',
            normalizer: recommendationNormalizer,
          },
          type: 'REQUEST_DATA_PUT_/RECOMMENDATIONS/V3?',
        })
      })

      it('should load the recommendations with page equals 1 when current recommendation is the final card', () => {
        // given
        const handleRequestSuccess = jest.fn()
        const handleRequestFail = jest.fn()
        const currentRecommendation = { mediationId: 'fin' }
        const recommendations = []
        const readRecommendations = null
        const shouldReloadRecommendations = false
        const functions = mapDispatchToProps(dispatch, props)
        const { loadRecommendations } = functions

        // when
        loadRecommendations(
          handleRequestSuccess,
          handleRequestFail,
          currentRecommendation,
          recommendations,
          readRecommendations,
          shouldReloadRecommendations
        )

        // then
        expect(dispatch.mock.calls[0][0]).toStrictEqual({
          config: {
            apiPath: `/recommendations/v3?`,
            body: {
              readRecommendations: null,
              seenRecommendationIds: [],
            },
            handleFail: handleRequestFail,
            handleSuccess: handleRequestSuccess,
            method: 'PUT',
            normalizer: recommendationNormalizer,
          },
          type: 'REQUEST_DATA_PUT_/RECOMMENDATIONS/V3?',
        })
      })

      it('should load the recommendations with page equals 1 when current recommendation has an empty mediation', () => {
        // given
        const handleRequestSuccess = jest.fn()
        const handleRequestFail = jest.fn()
        const currentRecommendation = { mediationId: 'vide' }
        const recommendations = []
        const readRecommendations = null
        const shouldReloadRecommendations = false
        const functions = mapDispatchToProps(dispatch, props)
        const { loadRecommendations } = functions

        // when
        loadRecommendations(
          handleRequestSuccess,
          handleRequestFail,
          currentRecommendation,
          recommendations,
          readRecommendations,
          shouldReloadRecommendations
        )

        // then
        expect(dispatch.mock.calls[0][0]).toStrictEqual({
          config: {
            apiPath: `/recommendations/v3?`,
            body: {
              readRecommendations: null,
              seenRecommendationIds: [],
            },
            handleFail: handleRequestFail,
            handleSuccess: handleRequestSuccess,
            method: 'PUT',
            normalizer: recommendationNormalizer,
          },
          type: 'REQUEST_DATA_PUT_/RECOMMENDATIONS/V3?',
        })
      })

      it('should load the recommendations with page equals 2 when current recommendation is a valid one attached to an offer', () => {
        // given
        const handleRequestSuccess = jest.fn()
        const handleRequestFail = jest.fn()
        const currentRecommendation = {
          id: 'ABC3',
          index: 1,
          offerId: 'ABC2',
        }
        const recommendations = [{ id: 'AE3', index: 3 }]
        const readRecommendations = null
        const shouldReloadRecommendations = false
        const functions = mapDispatchToProps(dispatch, props)
        const { loadRecommendations } = functions

        // when
        loadRecommendations(
          handleRequestSuccess,
          handleRequestFail,
          currentRecommendation,
          recommendations,
          readRecommendations,
          shouldReloadRecommendations
        )

        // then
        expect(dispatch.mock.calls[0][0]).toStrictEqual({
          config: {
            apiPath: `/recommendations/v3?`,
            body: {
              readRecommendations: null,
              seenRecommendationIds: ['AE3'],
            },
            handleFail: handleRequestFail,
            handleSuccess: handleRequestSuccess,
            method: 'PUT',
            normalizer: recommendationNormalizer,
          },
          type: 'REQUEST_DATA_PUT_/RECOMMENDATIONS/V3?',
        })
      })

      it('should make request with given geolocation to API', () => {
        // given
        const handleRequestSuccess = jest.fn()
        const handleRequestFail = jest.fn()
        const currentRecommendation = {
          id: 'ABC3',
          index: 1,
          offerId: 'ABC2',
        }
        const recommendations = [{ id: 'AE3', index: 3 }]
        const readRecommendations = null
        const shouldReloadRecommendations = false
        const functions = mapDispatchToProps(dispatch, props)
        const { loadRecommendations } = functions
        const coordinates = { latitude: 48.192, longitude: 1.291 }

        // when
        loadRecommendations(
          handleRequestSuccess,
          handleRequestFail,
          currentRecommendation,
          recommendations,
          readRecommendations,
          shouldReloadRecommendations,
          coordinates
        )

        // then
        expect(dispatch.mock.calls[0][0]).toStrictEqual({
          config: {
            apiPath: `/recommendations/v3?longitude=1.291&latitude=48.192`,
            body: {
              readRecommendations: null,
              seenRecommendationIds: ['AE3'],
            },
            handleFail: handleRequestFail,
            handleSuccess: handleRequestSuccess,
            method: 'PUT',
            normalizer: recommendationNormalizer,
          },
          type: 'REQUEST_DATA_PUT_/RECOMMENDATIONS/V3?LONGITUDE=1.291&LATITUDE=48.192',
        })
      })

      it('should load the recommendations when user is geolocated', () => {
        // given
        const handleRequestSuccess = jest.fn()
        const handleRequestFail = jest.fn()
        const currentRecommendation = {
          id: 'ABC3',
          index: 1,
          offerId: 'ABC2',
        }
        const recommendations = [{ id: 'AE3', index: 3 }]
        const readRecommendations = null
        const shouldReloadRecommendations = false
        const coordinates = {
          latitude: 2.8796567,
          longitude: 48.256756,
          watchId: 1,
        }
        const functions = mapDispatchToProps(dispatch, props)
        const { loadRecommendations } = functions

        // when
        loadRecommendations(
          handleRequestSuccess,
          handleRequestFail,
          currentRecommendation,
          recommendations,
          readRecommendations,
          shouldReloadRecommendations,
          coordinates
        )

        // then
        expect(dispatch.mock.calls[0][0]).toStrictEqual({
          config: {
            apiPath: `/recommendations/v3?longitude=48.256756&latitude=2.8796567`,
            body: {
              readRecommendations: null,
              seenRecommendationIds: ['AE3'],
            },
            handleFail: handleRequestFail,
            handleSuccess: handleRequestSuccess,
            method: 'PUT',
            normalizer: recommendationNormalizer,
          },
          type: 'REQUEST_DATA_PUT_/RECOMMENDATIONS/V3?LONGITUDE=48.256756&LATITUDE=2.8796567',
        })
      })

      it('should load the recommendations when user is not geolocated', () => {
        // given
        const handleRequestSuccess = jest.fn()
        const handleRequestFail = jest.fn()
        const currentRecommendation = {
          id: 'ABC3',
          index: 1,
          offerId: 'ABC2',
        }
        const recommendations = [{ id: 'AE3', index: 3 }]
        const readRecommendations = null
        const shouldReloadRecommendations = false
        const coordinates = {
          latitude: null,
          longitude: null,
          watchId: null,
        }
        const functions = mapDispatchToProps(dispatch, props)
        const { loadRecommendations } = functions

        // when
        loadRecommendations(
          handleRequestSuccess,
          handleRequestFail,
          currentRecommendation,
          recommendations,
          readRecommendations,
          shouldReloadRecommendations,
          coordinates
        )

        // then
        expect(dispatch.mock.calls[0][0]).toStrictEqual({
          config: {
            apiPath: `/recommendations/v3?`,
            body: {
              readRecommendations: null,
              seenRecommendationIds: ['AE3'],
            },
            handleFail: handleRequestFail,
            handleSuccess: handleRequestSuccess,
            method: 'PUT',
            normalizer: recommendationNormalizer,
          },
          type: 'REQUEST_DATA_PUT_/RECOMMENDATIONS/V3?',
        })
      })
    })

    describe('when mapping redirectHome', () => {
      it('should call setTimout 2000 times', () => {
        // when
        mapDispatchToProps(dispatch, props).redirectHome()

        // then
        expect(setTimeout).toHaveBeenCalledTimes(1)
        expect(setTimeout).toHaveBeenLastCalledWith(expect.any(Function), 2000)
      })

      it('should replace path by /connexion', () => {
        // given
        jest.useFakeTimers()

        // when
        mapDispatchToProps(dispatch, props).redirectHome()
        jest.runAllTimers()

        // then
        expect(replace).toHaveBeenCalledTimes(1)
        expect(replace).toHaveBeenLastCalledWith('/connexion')
      })
    })

    describe('when mapping redirectToFirstRecommendationIfNeeded', () => {
      describe('when there are no recommendations', () => {
        it('should return undefined', () => {
          // given
          const loadedRecommendations = []

          // when
          const redirect = mapDispatchToProps(
            dispatch,
            props
          ).redirectToFirstRecommendationIfNeeded(loadedRecommendations)

          // then
          expect(redirect).toBeUndefined()
        })
      })

      describe('when not on discovery pathname', () => {
        it('should return undefined', () => {
          // given
          const loadedRecommendations = [{ id: 'firstRecommendation' }]
          props.location.pathname = ''

          // when
          const redirect = mapDispatchToProps(
            dispatch,
            props
          ).redirectToFirstRecommendationIfNeeded(loadedRecommendations)

          // then
          expect(redirect).toBeUndefined()
        })
      })

      describe('when visiting for the first time', () => {
        it('should redirect to tuto recommendation with a specified mediation', () => {
          // given
          const dispatch = jest.fn()
          const loadedRecommendations = [{ id: 'QA3D', offerId: null, mediationId: 'A9' }]
          const ownProps = {
            history: {
              replace: jest.fn(),
            },
            match: {
              url: '/decouverte',
              params: {},
            },
          }

          // when
          mapDispatchToProps(dispatch, ownProps).redirectToFirstRecommendationIfNeeded(
            loadedRecommendations
          )

          // then
          expect(ownProps.history.replace).toHaveBeenCalledWith('/decouverte-v3/tuto/A9')
        })

        it('should redirect to tuto recommendation without mediation', () => {
          // given
          const dispatch = jest.fn()
          const loadedRecommendations = [{ id: 'QA3D', offerId: null, mediationId: null }]
          const ownProps = {
            history: {
              replace: jest.fn(),
            },
            match: {
              url: '/decouverte',
              params: {},
            },
          }

          // when
          mapDispatchToProps(dispatch, ownProps).redirectToFirstRecommendationIfNeeded(
            loadedRecommendations
          )

          // then
          expect(ownProps.history.replace).toHaveBeenCalledWith('/decouverte-v3/tuto/vide')
        })

        it('should delete tutos from store when leaving discovery', () => {
          // given
          const tutos = {
            id: 'ABCD',
          }

          // when
          mapDispatchToProps(dispatch, null).deleteTutorials(tutos)

          // then
          expect(dispatch).toHaveBeenCalledWith({
            config: {},
            patch: {
              recommendations: {
                id: 'ABCD',
              },
            },
            type: 'DELETE_DATA',
          })
        })
      })
    })

    describe('when mapping resetReadRecommendations', () => {
      it('should reset recommendations with the right configuration', () => {
        // when
        mapDispatchToProps(dispatch, props).resetReadRecommendations()

        // then
        expect(dispatch).toHaveBeenCalledWith({
          patch: { readRecommendations: [] },
          type: 'ASSIGN_DATA',
        })
      })
    })

    describe('when mapping saveLastRecommendationsRequestTimestamp', () => {
      it('should save recommendations loaded timestamp with the right configuration', () => {
        // when
        mapDispatchToProps(dispatch, props).saveLastRecommendationsRequestTimestamp()

        // then
        expect(dispatch).toHaveBeenCalledWith({
          type: 'SAVE_RECOMMENDATIONS_REQUEST_TIMESTAMP',
        })
      })
    })

    describe('when mapping updateLastRequestTimestamp', () => {
      it('should save update last seed request timestamp', () => {
        // when
        mapDispatchToProps(dispatch, props).updateLastRequestTimestamp()

        // then
        expect(dispatch.mock.calls[0][0]).toStrictEqual({
          seedLastRequestTimestamp: expect.any(Number),
          type: 'UPDATE_SEED_LAST_REQUEST_TIMESTAMP',
        })
      })
    })

    describe('when mapping resetRecommandations', () => {
      it('should delete all recommandations in the store', () => {
        // when
        mapDispatchToProps(dispatch, props).resetRecommendations()

        // then
        expect(dispatch).toHaveBeenCalledWith({
          patch: { recommendations: [] },
          type: 'ASSIGN_DATA',
        })
      })
    })
  })
})
