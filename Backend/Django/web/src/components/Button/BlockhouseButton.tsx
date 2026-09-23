import React from 'react'
import { StyleSheet, css } from 'aphrodite'

interface IBlockhouseButton {
  onClick: () => void
  type: 'clear' | 'solid' | 'grey'
  text: string
  fullWidth?: boolean;
}

const BlockhouseButton: React.FC<IBlockhouseButton> = (props) => {
    let buttonStyle;
    switch(props.type) {
        case 'solid' :
            buttonStyle = styles.blockhouseButtonSolid;
            break;
        case 'clear':
            buttonStyle = styles.blockhouseButtonClear
            break;
        case 'grey':
            buttonStyle = styles.blockhouseButtonGrey
            break;
    }
    const applyButtonWidth = props.fullWidth ? styles.buttonWidth : null
    return (
            <button className={css(styles.BlockhouseButtonContainer, buttonStyle, applyButtonWidth)} onClick={props.onClick}>
                {props.text}
            </button>
    )
}

const styles = StyleSheet.create({
  BlockhouseButtonContainer: {
    all: 'unset',
    borderRadius: '5px',
    padding: '8px',
    cursor: 'pointer',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center'
  },
  blockhouseButtonSolid: {
    backgroundColor: 'white',
    color: 'black'
  },
  blockhouseButtonClear: {
    color: 'white'
  },
  blockhouseButtonGrey: {
    backgroundColor: '#3D3D3D',
    color: 'white'
  },
  buttonWidth: {
    width: '100%'
  }
});

export default BlockhouseButton
