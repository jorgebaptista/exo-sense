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
  it('renders the ExoSense application', () => {
    render(<Home />)
    
    // Check if the page contains ExoSense content
    expect(screen.getByText('ExoSense')).toBeInTheDocument()
    expect(screen.getByText('Hunt for Exoplanets with AI')).toBeInTheDocument()
    expect(screen.getByText('Upload light curve data to detect potential exoplanets using machine learning')).toBeInTheDocument()
  })

  it('has the upload section', () => {
    render(<Home />)
    
    const uploadText = screen.getByText('Drop your data file here')
    expect(uploadText).toBeInTheDocument()
    
    const analyzeButton = screen.getByText('Analyze for Exoplanets')
    expect(analyzeButton).toBeInTheDocument()
  })
})