/**
 * Unit tests for NWChem Input Parser (nw.ts)
 */

import {
  NWChemParser,
  parseNWChemSource,
  getLineKeywords,
  GeometryBlock,
  BasisBlock,
  SCFBlock,
  TaskDirective,
} from '../../src/parsers/nw';

describe('NWChemParser', () => {
  // Basic parsing tests
  describe('Basic Parsing', () => {
    it('should parse empty source', () => {
      const parser = new NWChemParser('');
      expect(parser.getAllSections()).toEqual([]);
    });

    it('should parse source with comments', () => {
      const source = `# This is a comment
# Another comment`;
      const parser = new NWChemParser(source);
      expect(parser.getAllSections()).toEqual([]);
    });

    it('should get line keywords', () => {
      expect(getLineKeywords('start molecule')).toEqual(['start', 'molecule']);
      expect(getLineKeywords('  # comment')).toEqual([]);
      expect(getLineKeywords('')).toEqual([]);
    });
  });

  // Geometry Block Tests
  describe('Geometry Block Parsing', () => {
    it('should parse geometry block with atoms', () => {
      const source = `geometry
  C 0.0 0.0 0.0
  H 1.0 0.0 0.0
  H 0.0 1.0 0.0
  H 0.0 0.0 1.0
end`;
      const parser = new NWChemParser(source);
      const geometry = parser.parseGeometryBlock();
      
      expect(geometry).not.toBeNull();
      expect(geometry!.units).toBe('angstroms');
      expect(geometry!.coordinates).toHaveLength(4);
      expect(geometry!.coordinates[0]).toEqual({
        element: 'C',
        x: 0.0,
        y: 0.0,
        z: 0.0,
      });
    });

    it('should parse geometry with units specification', () => {
      const source = `geometry
  units bohr
  H 0.0 0.0 0.0
end`;
      const parser = new NWChemParser(source);
      const geometry = parser.parseGeometryBlock();
      
      expect(geometry!.units).toBe('bohr');
      expect(geometry!.coordinates).toHaveLength(1);
    });

    it('should parse geometry with atom tags', () => {
      const source = `geometry
  C 0.0 0.0 0.0 carbon1
  O 1.2 0.0 0.0 oxygen1
end`;
      const parser = new NWChemParser(source);
      const geometry = parser.parseGeometryBlock();
      
      expect(geometry!.coordinates[0].tag).toBe('carbon1');
      expect(geometry!.coordinates[1].tag).toBe('oxygen1');
    });

    it('should return null when no geometry block', () => {
      const parser = new NWChemParser('start molecule');
      expect(parser.parseGeometryBlock()).toBeNull();
    });
  });

  // Basis Block Tests
  describe('Basis Block Parsing', () => {
    it('should parse basis block with library', () => {
      const source = `basis
  * library 6-31g*
end`;
      const parser = new NWChemParser(source);
      const basisBlocks = parser.parseBasisBlock();
      
      expect(basisBlocks).toHaveLength(1);
      expect(basisBlocks[0].basisSet).toBe('6-31g*');
      expect(basisBlocks[0].library).toBe(true);
    });

    it('should parse basis block with explicit elements', () => {
      const source = `basis
  C library cc-pvdz
  H library cc-pvdz
end`;
      const parser = new NWChemParser(source);
      const basisBlocks = parser.parseBasisBlock();
      
      expect(basisBlocks[0].elements).toContain('C');
      expect(basisBlocks[0].elements).toContain('H');
    });

    it('should return empty array when no basis block', () => {
      const parser = new NWChemParser('geometry\nend');
      expect(parser.parseBasisBlock()).toEqual([]);
    });
  });

  // SCF Block Tests
  describe('SCF Block Parsing', () => {
    it('should parse SCF block with maxiter', () => {
      const source = `scf
  maxiter 50
end`;
      const parser = new NWChemParser(source);
      const scf = parser.parseSCFBlock();
      
      expect(scf).not.toBeNull();
      expect(scf!.maxiter).toBe(50);
    });

    it('should parse SCF block with thresh', () => {
      const source = `scf
  thresh 1e-6
end`;
      const parser = new NWChemParser(source);
      const scf = parser.parseSCFBlock();
      
      expect(scf!.thresh).toBe(1e-6);
    });

    it('should parse SCF block with tol2e', () => {
      const source = `scf
  tol2e 1e-8
end`;
      const parser = new NWChemParser(source);
      const scf = parser.parseSCFBlock();
      
      expect(scf!.tol2e).toBe(1e-8);
    });

    it('should parse SCF block with direct', () => {
      const source = `scf
  direct
end`;
      const parser = new NWChemParser(source);
      const scf = parser.parseSCFBlock();
      
      expect(scf!.direct).toBe(true);
    });

    it('should parse SCF block with vectors', () => {
      const source = `scf
  vectors input atomic
end`;
      const parser = new NWChemParser(source);
      const scf = parser.parseSCFBlock();
      
      expect(scf!.vectors).toBe('input atomic');
    });

    it('should parse complete SCF block', () => {
      const source = `scf
  maxiter 100
  thresh 1e-7
  tol2e 1e-9
  direct
  vectors input atomic
end`;
      const parser = new NWChemParser(source);
      const scf = parser.parseSCFBlock();
      
      expect(scf).toEqual({
        maxiter: 100,
        thresh: 1e-7,
        tol2e: 1e-9,
        direct: true,
        vectors: 'input atomic',
      });
    });
  });

  // Task Directive Tests
  describe('Task Directive Parsing', () => {
    it('should parse single task directive', () => {
      const source = 'task scf energy';
      const parser = new NWChemParser(source);
      const tasks = parser.parseTaskDirectives();
      
      expect(tasks).toHaveLength(1);
      expect(tasks[0]).toEqual({ theory: 'scf', operation: 'energy' });
    });

    it('should parse multiple task directives', () => {
      const source = `task scf energy
task dft optimize
task mp2 frequency`;
      const parser = new NWChemParser(source);
      const tasks = parser.parseTaskDirectives();
      
      expect(tasks).toHaveLength(3);
      expect(tasks[0]).toEqual({ theory: 'scf', operation: 'energy' });
      expect(tasks[1]).toEqual({ theory: 'dft', operation: 'optimize' });
      expect(tasks[2]).toEqual({ theory: 'mp2', operation: 'frequency' });
    });

    it('should default to energy when operation not specified', () => {
      const source = 'task scf';
      const parser = new NWChemParser(source);
      const tasks = parser.parseTaskDirectives();
      
      expect(tasks[0].operation).toBe('energy');
    });

    it('should ignore comments', () => {
      const source = `# Task directive
task scf energy`;
      const parser = new NWChemParser(source);
      const tasks = parser.parseTaskDirectives();
      
      expect(tasks).toHaveLength(1);
    });
  });

  // Section Management Tests
  describe('Section Management', () => {
    it('should get all sections', () => {
      const source = `geometry
end
basis
end
scf
end`;
      const parser = new NWChemParser(source);
      const sections = parser.getAllSections();
      
      expect(sections).toContain('geometry');
      expect(sections).toContain('basis');
      expect(sections).toContain('scf');
    });

    it('should get section content', () => {
      const source = `geometry
  C 0.0 0.0 0.0
end`;
      const parser = new NWChemParser(source);
      const sections = parser.getSectionContent('geometry');
      
      expect(sections).toHaveLength(1);
      expect(sections[0].name).toBe('geometry');
    });

    it('should get section at line', () => {
      const source = `geometry
  C 0.0 0.0 0.0
end`;
      const parser = new NWChemParser(source);
      
      expect(parser.getSectionAtLine(0)).toBe('geometry');
      expect(parser.getSectionAtLine(1)).toBe('geometry');
      expect(parser.getSectionAtLine(2)).toBe('geometry');
      expect(parser.getSectionAtLine(10)).toBeNull();
    });
  });

  // Syntax Validation Tests
  describe('Syntax Validation', () => {
    it('should validate correct syntax', () => {
      const source = `geometry
end`;
      const parser = new NWChemParser(source);
      const result = parser.isValidSyntax();
      
      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    it('should detect unclosed section', () => {
      const source = `geometry
  C 0.0 0.0 0.0`;
      const parser = new NWChemParser(source);
      const result = parser.isValidSyntax();
      
      expect(result.valid).toBe(false);
      expect(result.errors).toHaveLength(1);
      expect(result.errors[0].message).toContain('Unclosed section');
    });

    it('should detect unexpected end', () => {
      const source = `end`;
      const parser = new NWChemParser(source);
      const result = parser.isValidSyntax();
      
      expect(result.valid).toBe(false);
      expect(result.errors[0].message).toContain('Unexpected');
    });
  });

  // Context Tests
  describe('Context Parsing', () => {
    it('should get context at position', () => {
      const source = `geometry
  C 0.0 0.0 0.0
end`;
      const parser = new NWChemParser(source);
      const context = parser.getContext(1, 5);
      
      expect(context.currentSection).toBe('geometry');
      expect(context.lineContent).toBe('  C 0.0 0.0 0.0');
      expect(context.isInBlock).toBe(true);
    });

    it('should get word at cursor', () => {
      const source = 'start water';
      const parser = new NWChemParser(source);
      const context = parser.getContext(0, 8);
      
      expect(context.wordAtCursor).toBe('water');
    });

    it('should get completion context', () => {
      const source = 'task scf';
      const parser = new NWChemParser(source);
      const completion = parser.getCompletionContext(0, 8);
      
      expect(completion.type).toBe('task_operation');
      expect(completion.section).toBeNull();
    });
  });

  // Full Integration Test
  describe('Full Input File Parsing', () => {
    it('should parse complete NWChem input', () => {
      const source = `start water

title "Water molecule"

geometry
  O 0.0 0.0 0.0
  H 0.757 0.586 0.0
  H -0.757 0.586 0.0
end

basis
  * library 6-31g*
end

scf
  maxiter 50
  thresh 1e-6
end

task scf energy`;

      const parser = new NWChemParser(source);
      
      // Check sections
      expect(parser.getAllSections()).toContain('geometry');
      expect(parser.getAllSections()).toContain('basis');
      expect(parser.getAllSections()).toContain('scf');
      
      // Check geometry
      const geometry = parser.parseGeometryBlock();
      expect(geometry!.coordinates).toHaveLength(3);
      
      // Check basis
      const basis = parser.parseBasisBlock();
      expect(basis[0].library).toBe(true);
      
      // Check SCF
      const scf = parser.parseSCFBlock();
      expect(scf!.maxiter).toBe(50);
      
      // Check task
      const tasks = parser.parseTaskDirectives();
      expect(tasks).toHaveLength(1);
      expect(tasks[0].theory).toBe('scf');
      
      // Check syntax
      const validation = parser.isValidSyntax();
      expect(validation.valid).toBe(true);
    });
  });
});
