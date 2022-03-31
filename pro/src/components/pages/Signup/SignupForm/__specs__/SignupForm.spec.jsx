import '@testing-library/jest-dom'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createBrowserHistory } from 'history'
import React from 'react'
import { Provider } from 'react-redux'
import { Router } from 'react-router-dom'

import { configureTestStore } from 'store/testUtils'

import SignupForm from '../SignupForm'

const renderSignupForm = async ({ props, storeOverride = {} }) => {
  const store = configureTestStore(storeOverride)
  const history = createBrowserHistory()
  const routerProps = {
    history,
    location: history.location,
  }
  const rtlReturns = render(
    <Provider store={store}>
      <Router history={history}>
        <SignupForm {...props} {...routerProps} />
      </Router>
    </Provider>
  )

  await screen.findByText('Créer votre compte professionnel')

  return {
    history,
    rtlReturns,
  }
}

describe('src | components | pages | Signup | SignupForm', () => {
  let props
  let store

  beforeEach(() => {
    props = {
      createNewProUser: jest.fn(),
      notifyError: () => {},
      redirectToConfirmation: jest.fn(),
      showNotification: jest.fn(),
    }
    store = {
      data: {
        users: null,
      },
      features: {
        list: [{ isActive: true, nameKey: 'ENABLE_PRO_ACCOUNT_CREATION' }],
      },
    }
  })

  it('should redirect to home page if the user is logged in', async () => {
    // when the user is logged in and lands on signup validation page
    store.data.users = [{ id: 'CMOI' }]
    const { history } = await renderSignupForm({ props, storeOverride: store })

    // then he should be redirected to home page
    await waitFor(() => {
      expect(history.location.pathname).toBe('/')
    })
  })

  describe('render', () => {
    it('should render with all information', async () => {
      // when the user sees the form
      await renderSignupForm({ props, storeOverride: store })

      // then it should have a title
      expect(
        screen.getByRole('heading', {
          name: /Créer votre compte professionnel/,
        })
      ).toBeInTheDocument()
      // and a subtitle
      expect(
        screen.getByRole('heading', {
          name: /Merci de compléter les champs suivants pour créer votre compte./,
        })
      ).toBeInTheDocument()
      // and an external link to the help center
      expect(
        screen.getByRole('link', {
          name: /Consulter notre centre d’aide/,
        })
      ).toHaveAttribute(
        'href',
        'https://passculture.zendesk.com/hc/fr/articles/4411999179665'
      )
      // and an external link to CGU
      expect(
        screen.getByRole('link', {
          name: /Conditions Générales d’Utilisation/,
        })
      ).toHaveAttribute('href', 'https://pass.culture.fr/cgu-professionnels/')
      // and an external link to GDPR chart
      expect(
        screen.getByRole('link', {
          name: /Charte des Données Personnelles/,
        })
      ).toHaveAttribute('href', 'https://pass.culture.fr/donnees-personnelles/')
      // and a mail to support
      expect(
        screen.getByRole('link', {
          name: /contactez notre support/,
        })
      ).toHaveAttribute('href', 'mailto:support-pro@passculture.app')

      // and a RGS link
      expect(
        screen.getByRole('link', {
          name: /Consulter nos recommandations de sécurité/,
        })
      ).toHaveAttribute(
        'href',
        'https://aide.passculture.app/hc/fr/articles/4458607720732--Acteurs-Culturels-Comment-assurer-la-s%C3%A9curit%C3%A9-de-votre-compte-'
      )
      // and a link to signin page
      expect(
        screen.getByRole('link', {
          name: /J’ai déjà un compte/,
        })
      ).toHaveAttribute('href', '/connexion')
    })

    it('should render with all fields', async () => {
      // when the user sees the form
      await renderSignupForm({ props, storeOverride: store })

      // then it should have an email field
      expect(
        screen.getByRole('textbox', {
          name: /Adresse e-mail/,
        })
      ).toBeInTheDocument()
      // and a password field
      expect(screen.getByLabelText(/Mot de passe/)).toBeInTheDocument()
      // and a last name field
      expect(
        screen.getByRole('textbox', {
          name: /Nom/,
        })
      ).toBeInTheDocument()
      // and a first name field
      expect(
        screen.getByRole('textbox', {
          name: /Prénom/,
        })
      ).toBeInTheDocument()
      // and a telephone field
      expect(
        screen.getByRole('textbox', {
          name: /Téléphone/,
        })
      ).toBeInTheDocument()
      // and a SIREN field
      expect(
        screen.getByRole('textbox', {
          name: /SIREN de la structure que vous représentez/,
        })
      ).toBeInTheDocument()
      // and a contact field
      expect(
        screen.getByRole('checkbox', {
          name: /pour recevoir les nouveautés du pass Culture et contribuer à son amélioration/,
        })
      ).toBeInTheDocument()
      // and a submit button
      expect(
        screen.getByRole('button', {
          name: /Créer mon compte/,
        })
      ).toBeInTheDocument()
    })

    it('should enable submit button only when required inputs are filled', async () => {
      // Given the signup form
      await renderSignupForm({ props, storeOverride: store })

      const submitButton = screen.getByRole('button', {
        name: /Créer mon compte/,
      })
      // when the user fills required information
      userEvent.paste(
        screen.getByRole('textbox', {
          name: /Adresse e-mail/,
        }),
        'test@example.com'
      )
      userEvent.paste(screen.getByLabelText(/Mot de passe/), 'user@AZERTY123')
      userEvent.paste(
        screen.getByRole('textbox', {
          name: /Nom/,
        }),
        'Nom'
      )
      userEvent.paste(
        screen.getByRole('textbox', {
          name: /Prénom/,
        }),
        'Prénom'
      )
      userEvent.paste(
        screen.getByRole('textbox', {
          name: /Téléphone/,
        }),
        '0722332233'
      )
      expect(submitButton).toBeDisabled()

      fetch.mockResponse(
        JSON.stringify({
          unite_legale: {
            denomination: 'nom du lieu',
            siren: '881457238',
            etablissement_siege: {
              geo_l4: '3 rue de la gare',
              libelle_commune: 'paris',
              latitude: 1.1,
              longitude: 1.1,
              code_postal: '75000',
            },
          },
        }),
        {
          status: 200,
        }
      )
      userEvent.paste(
        screen.getByRole('textbox', {
          name: /SIREN/,
        }),
        '881457238'
      )
      // await the end of async calls trigger by siren field.
      await screen.findByDisplayValue('881457238')
      // then it should enable submit button
      expect(submitButton).toBeEnabled()
    })
  })
})
