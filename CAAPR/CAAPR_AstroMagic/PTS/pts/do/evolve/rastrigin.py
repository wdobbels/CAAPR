
from pts.evolve.simplega import GAEngine, RawScoreCriteria
from pts.evolve.genomes.list1d import G1DList
from pts.evolve import Mutators, Initializators
from pts.evolve import Selectors
from pts.evolve import Consts
import math

# This is the Rastrigin Function, a deception function
def rastrigin(genome):
    
   n = len(genome)
   total = 0
   for i in xrange(n):
      total += genome[i]**2 - 10*math.cos(2*math.pi*genome[i])
      
   return (10*n) + total

def run_main():
    
   # Genome instance
   genome = G1DList(20)
   genome.setParams(rangemin=-5.2, rangemax=5.30, bestrawscore=0.00, rounddecimal=2)
   genome.initializator.set(Initializators.G1DListInitializatorReal)
   genome.mutator.set(Mutators.G1DListMutatorRealGaussian)

   genome.evaluator.set(rastrigin)

   # Genetic Algorithm Instance
   ga = GAEngine(genome)
   ga.terminationCriteria.set(RawScoreCriteria)
   ga.setMinimax(Consts.minimaxType["minimize"])
   ga.setGenerations(3000)
   ga.setCrossoverRate(0.8)
   ga.setPopulationSize(100)
   ga.setMutationRate(0.06)

   ga.evolve(freq_stats=50)

   best = ga.bestIndividual()
   print best

if __name__ == "__main__":
   run_main()