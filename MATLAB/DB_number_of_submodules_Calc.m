function [NoofSM_per_arm_mtx,NoofSM_total_mtx] = DB_number_of_submodules_Calc(Uph_mtx,U_sm_mtx,Noofarms_per_phase_mtx,NoofPhases_mtx)
% Function calculates the total number of submodules 
%
% [NoofSM_per_arm_mtx,NoofSM_total_mtx] = DB_Number_of_submodules_Calc(Uph_mtx,U_sm_mtx,Noofarms_per_phase_mtx,NoofPhases_mtx)
%
% NoofSM_per_arm_mtx --> Number of arms per submodule vector 
% NoofSM_total_mtx --> Total number of submodules vector 
% Uph_mtx --> output phase voltage vector 
% U_sm_mtx --> submodule output RMS voltage vector
% Noofarms_per_phase_mtx --> Number of arms per submodules vector
% NoofPhases_mtx --> Number of phases vector

% number of submodules per arm
NoofSM_per_arm_mtx = Uph_mtx*sqrt(2)./U_sm_mtx; 
% number of submodules per arm
NoofSM_total_mtx = NoofSM_per_arm_mtx.*Noofarms_per_phase_mtx.*NoofPhases_mtx; 