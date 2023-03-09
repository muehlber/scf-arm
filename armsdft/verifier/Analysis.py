from collections import namedtuple

from armsdft.verifier.AnalysisResult import AnalysisResult
from armsdft.verifier.AssignmentCollection import AssignmentCollection
from armsdft.verifier.SecurityLevel import SecurityLevel
from armsdft.verifier.exceptions.BranchtimeDiffersException import BranchtimeDiffersException
from armsdft.verifier.exceptions.LoopOnHighConditionException import LoopOnHighConditionException
from armsdft.verifier.exceptions.NemisisOnHighConditionException import NemisisOnHighConditionException


class Analysis:
    result = namedtuple('result', ['result', 'ep', 'finishing_ac', 'assignments', 'unique_ret'])

    def __init__(self, program):
        self.program = program

    def analyze(self, starting_ep, initial_ac, finishing_ac, timing_sensitive=True):
  
        assignments = {}
        self.program.set_entry_point(starting_ep)
        unique_ret = len(self.program.possible_exit_points) == 1

        pending_ep = [starting_ep]
        while len(pending_ep) > 0:
            print("pending_ep: ", pending_ep)
            current_ep = pending_ep.pop(0)
            current_instr = self.program.get_instruction_at_execution_point(current_ep)
            print("current inst: ", current_instr)
            current_predecessors = current_instr.predecessors_list
            print("current_predecessors: ", current_predecessors)

            # Build up AssignmentCollection that is passed to the instruction
            # for processing. If this is the first instruction, then current_ac
            # equals the initial_ac. Else, it is the least upper bound of all
            # ACs that are coming from predecessors of the current_ep

            return_later = False
            current_ac = AssignmentCollection.bottom()
            if len(current_predecessors) == 0:
                # Case: current_ep == starting_ep
                current_ac = current_ac & initial_ac
            else:  
                
                for pred_ep in current_predecessors:
                    pred_ac = assignments.get(pred_ep, None)
                    if pred_ac is None:
                        return_later = True
                    else:
                        current_ac = current_ac & pred_ac

            current_ac.reset()
            try:
                if(not return_later):
                    current_instr.execute_judgment(current_ac)
            except BranchtimeDiffersException:
                if timing_sensitive:
                    assignments[current_ep] = current_ac
                    return Analysis.result(AnalysisResult.TIMING_LEAK, current_ep, None, assignments, unique_ret)
                else:
                    pass
            except LoopOnHighConditionException:
                if timing_sensitive:
                    assignments[current_ep] = current_ac
                    return Analysis.result(AnalysisResult.LOOP_ON_SECRET_DATA, current_ep, None, assignments, unique_ret)
            except NemisisOnHighConditionException:
                if timing_sensitive:
                    assignments[current_ep] = current_ac
                    return Analysis.result(AnalysisResult.NEMISIS_VULNERABILITY, current_ep, None, assignments, unique_ret)
                else:
                    pass       

            if current_ac.is_modified() or (assignments.get(current_ep, None) is None):
                if not return_later:
                    if(len(current_instr.get_successors_checked()) == 2):
                        pending_ep.insert(0, current_instr.get_successors_checked()[0])
                        pending_ep.insert(1, current_instr.get_successors_checked()[1])
                    if(len(current_instr.get_successors_checked()) == 1):
                        pending_ep.insert(0, current_instr.get_successors_checked()[0])
            
                #pending_ep.extend(current_instr.get_successors_checked())
            if return_later:
                print("retuen_later happened")
                #pending_ep.append(current_ep)

            if not return_later:
                assignments[current_ep] = current_ac

        last_ac = AssignmentCollection.bottom()
        for last_ep in self.program.possible_exit_points:
            last_ac = last_ac & assignments.get(last_ep)

        if last_ac <= finishing_ac:
            for key in self.program.mem_map.keys():
                if(last_ac.mem.get(key) == SecurityLevel.HIGH):
                    print(key, ": ", last_ac.mem.get(key))
            return Analysis.result(AnalysisResult.SUCCESS, None, last_ac, assignments, unique_ret)
        else:
            error_ep = self._determine_error_ep(initial_ac, finishing_ac, assignments)
            for key in self.program.mem_map.keys():
                if(last_ac.mem.get(key) == SecurityLevel.HIGH):
                    print(key, ": ", last_ac.mem.get(key))
            return Analysis.result(AnalysisResult.INFORMATION_LEAK, error_ep, last_ac, assignments, unique_ret)

    def _get_error_assignments(self, ac1, ac2):
        return {'r' + str(i) for i in range(16) if not ac1.ra.get('r' + str(i)) <= ac2.ra.get('r' + str(i))}


    def _determine_error_ep(self, starting_ac, finishing_ac, assignments):
        for exit_ep in self.program.possible_exit_points:
            error_ra = self._get_error_assignments(assignments[exit_ep], finishing_ac)
            if len(error_ra) == 0:
                continue
            visited = set()
            to_visit = [exit_ep]

            while len(to_visit) > 0:
                current_ep = to_visit.pop(0)
                visited.add(current_ep)

                pred = self.program.get_instruction_at_execution_point(current_ep).predecessors_list
                if len(pred) == 0:
                    current_ac = starting_ac
                else:
                    current_ac = AssignmentCollection.bottom()

                for pred_ep in pred:
                    if pred_ep not in visited:
                        to_visit.append(pred_ep)
                    current_ac = current_ac & assignments[pred_ep]

                if error_ra != self._get_error_assignments(current_ac, finishing_ac):
                    return current_ep

        return None
