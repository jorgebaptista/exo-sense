import { render, screen } from '@testing-library/react'
import Home from '../app/page'

// Mock Next.js Image component
jest.mock('next/image', () => ({
  __esModule: true,
  default: ({ src, alt, ...props }: { src: string; alt: string; [key: string]: unknown }) => {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={src} alt={alt} {...props} />
  },
}))

describe('Home Page', () => {
  it('renders the main page content', () => {
    render(<Home />)
    
    // Check if the page contains expected elements
    expect(screen.getByText('Get started by editing')).toBeInTheDocument()
    expect(screen.getByText('Deploy now')).toBeInTheDocument()
    expect(screen.getByText('Read our docs')).toBeInTheDocument()
  })

  it('has the correct Next.js logo', () => {
    render(<Home />)
    
    const logo = screen.getByAltText('Next.js logo')
    expect(logo).toBeInTheDocument()
  })
})