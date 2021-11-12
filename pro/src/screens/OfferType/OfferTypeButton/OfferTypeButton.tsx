import cn from 'classnames'
import React, { FunctionComponent, SVGProps } from 'react'

import { ReactComponent as TickIcon } from 'icons/tick.svg'

import styles from './OfferTypeButton.module.scss'

interface IOfferTypeButton {
  isSelected: boolean;
  Icon: FunctionComponent<SVGProps<SVGSVGElement> & { title?: string | undefined; }>;
  label: string;
  onClick?: () => void;
  className?: string;
}

const OfferTypeButton = ({
  isSelected,
  Icon,
  label,
  onClick,
  className,
}: IOfferTypeButton): JSX.Element => (
  <label className={cn(styles.button, { [styles['is-selected']]: isSelected }, className)}>
    {isSelected ? <TickIcon className={styles['button-check-mark']} /> : null}
    <Icon className={styles['button-icon']} />
    <input
      checked={isSelected}
      className={styles['button-radio']}
      name='offer-type'
      onClick={onClick}
      type='radio'
    />
    {label}
  </label>
)

export default OfferTypeButton
