function [X_norm,f] = FFT_fn1d(x,t)
% FFT of a signal along 1st dimension
% x input data
% t - Time vector 

L = length(x); % Sample length
dt = mean(diff(t)); % sampling period
fs= 1/dt; % sampling frequency

% figure(1)
% subplot(311)
% plot(t*1000,data)
% title('Data')
% xlabel('time [ms]')
% ylabel('X(t)')

Y = fft(x); % Computing FFT
P2 = Y/L; % Dual side-band spectrum

X = P2(1:L/2+1); % single sided spectrum based on even value of L
X(2:end-1) = 2*X(2:end-1);

f = fs*(0:(L/2))/L; % frequency 

% mf = 

% f_idx = find(f < f_fun + mean(diff(f))/2 & f > f_fun - mean(diff(f))/2 );% Index corresponding to fundamental

X_norm = X/sqrt(2);
X_norm(1) = X(1);% Normalized Spectra with respect to the Fundamental 

% subplot(3,1,2:3)
% bar(f,P1/P1(f_idx)) 
% grid on
% title('Single-Sided Amplitude Spectrum of Data)')
% xlabel('Harmonic order')
% ylabel('|X(f)|')
% xlim([0 50])