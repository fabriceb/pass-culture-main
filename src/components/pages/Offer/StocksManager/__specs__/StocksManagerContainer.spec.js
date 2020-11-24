import { mapStateToProps } from '../StocksManagerContainer'

describe('src | components | pages | Offer | StocksManagerContainer | mapStateToProps', () => {
  let state
  let props

  beforeEach(() => {
    state = {
      data: {
        providers: [],
        products: [{ id: 'B1', lastProviderId: 'C1' }],
        stocks: [{ offerId: 'A1' }],
      },
      offers: {
        list: [
          {
            id: 'A1',
            isEvent: true,
            isThing: false,
            productId: 'B1',
          },
        ],
      },
    }
    props = {
      offerId: 'A1',
      match: {},
    }
  })

  describe('mapStateToProps', () => {
    it('should return an empty object when offer was not found', () => {
      // given
      props.offerId = 'A2'

      // when
      const result = mapStateToProps(state, props)

      // then
      expect(result).toStrictEqual({})
    })

    it('should return an object when offer was found', () => {
      // when
      const result = mapStateToProps(state, props)

      // then
      expect(result).toStrictEqual({
        isEvent: true,
        isStockCreationAllowed: true,
        offer: {
          id: 'A1',
          isEvent: true,
          isThing: false,
          productId: 'B1',
        },
        product: {
          id: 'B1',
          lastProviderId: 'C1',
        },
        provider: undefined,
        stocks: [
          {
            offerId: 'A1',
          },
        ],
      })
    })

    describe('isStockCreationAllowed', () => {
      it('should be true when offer is an event', () => {
        // given
        state.offers.list[0].isEvent = true
        state.offers.list[0].isThing = false

        // when
        const result = mapStateToProps(state, props)

        // then
        expect(result).toHaveProperty('isStockCreationAllowed', true)
      })

      it('should be true when there is no stock', () => {
        // given
        state.offers.list[0].isEvent = false
        state.offers.list[0].isThing = true
        state.data.stocks = []

        // when
        const result = mapStateToProps(state, props)

        // then
        expect(result).toHaveProperty('isStockCreationAllowed', true)
      })

      it('should be false when offer is a thing and there is one stock', () => {
        // given
        state.offers.list[0].isEvent = false
        state.offers.list[0].isThing = true
        state.data.stocks = [{ offerId: 'A1' }]

        // when
        const result = mapStateToProps(state, props)

        // then
        expect(result).toHaveProperty('isStockCreationAllowed', false)
      })
    })
  })
})
