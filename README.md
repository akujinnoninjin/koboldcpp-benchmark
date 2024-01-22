# koboldcpp-benchmark

Quick and dirty benchmarking script for testing processor configs with kcpp. 

- Uses numactl to thread pin in a variety of configs. (Single socket/dual socket, favoring filling all physical threads evenly before virtual threads)
- Interleaves memory as appropriate
- Uses fixed seeds for repeatability
- Outputs generation data to a csv file for processing.
